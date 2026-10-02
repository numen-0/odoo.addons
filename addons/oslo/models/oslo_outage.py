from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class OsloOutage(models.Model):
    _name = "oslo.outage"
    _description = "Production Outage"
    _order = "started_at desc"

    description = fields.Char(
        string="Description",
        required=True,
    )

    started_at = fields.Datetime(
        string="Started At",
        default=fields.Datetime.now,
        required=True,
        readonly=True,
    )

    ended_at = fields.Datetime(
        string="Ended At",
        readonly=True,
    )

    started_by = fields.Many2one(
        "res.users",
        string="Started By",
        readonly=True,
        default=lambda self: self.env.user,
    )

    ended_by = fields.Many2one(
        "res.users",
        string="Ended By",
        readonly=True,
    )

    is_active = fields.Boolean(
        string="Active",
        compute="_compute_is_active",
        store=True,
    )

    @api.depends("ended_at")
    def _compute_is_active(self):
        for outage in self:
            outage.is_active = not outage.ended_at

    @api.constrains("started_at", "ended_at")
    def _check_dates(self):
        for outage in self:
            if outage.ended_at and outage.ended_at < outage.started_at:
                raise ValidationError(
                    "The end date cannot be before the start date."
                )

    @api.constrains("is_active")
    def _check_single_active(self):
        for outage in self:
            if outage.is_active:
                active_count = self.search_count([
                    ("is_active", "=", True),
                    ("id", "!=", outage.id),
                ])

                if active_count:
                    raise ValidationError(
                        "Only one outage can be active at a time."
                    )

    def _check_operator_access(self):
        if not (
            self.env.user.has_group("oslo.group_oslo_operator")
            or self.env.user.has_group("oslo.group_oslo_manager")
        ):
            raise UserError(
                "You do not have permission to start or end an outage."
            )

    @api.model
    def action_start_outage(self, description="Production outage"):
        self._check_operator_access()

        if self.search_count([("is_active", "=", True)]):
            raise UserError("There is already an active outage.")

        return self.create({
            "description": description,
            "started_by": self.env.user.id,
        })

    def action_end_outage(self):
        self._check_operator_access()

        for outage in self:
            if not outage.is_active:
                raise UserError("This outage has already ended.")

            outage.write({
                "ended_at": fields.Datetime.now(),
                "ended_by": self.env.user.id,
            })

        return True

    @api.model
    def get_dashboard_data(self):
        active_outage = self.search(
            [("is_active", "=", True)],
            limit=1,
        )

        if active_outage:
            return {
                "id": active_outage.id,
                "is_active": True,
                "started_at": active_outage.started_at,
                "started_by": active_outage.started_by.name,
                "last_outage_ended_at": False,
            }

        last_outage = self.search(
            [("ended_at", "!=", False)],
            order="ended_at desc",
            limit=1,
        )

        return {
            "id": False,
            "is_active": False,
            "started_at": False,
            "started_by": False,
            "last_outage_ended_at": (
                last_outage.ended_at if last_outage else False
            ),
        }

    @api.model
    def get_reliability_data(self, days=30):

        #* Date range

        days = int(days)
        if days not in (7, 30, 90, 365):
            days = 30

        now = fields.Datetime.to_datetime(fields.Datetime.now())
        assert now is not None

        # Note: range includes today
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_start = today - timedelta(days=days - 1)

        outages = self.search([
            ("started_at", "<", now),
            "|",
            ("ended_at", "=", False),
            ("ended_at", ">", period_start),
        ])

        #* Metrics

        total_downtime = 0.0
        completed_count = 0
        durations = []
        daily = {}

        for offset in range(days):
            day = (period_start + timedelta(days=offset)).date()
            daily[day.isoformat()] = {
                "date": day.isoformat(),
                "count": 0,
                "downtime_seconds": 0,
            }

        for outage in outages:
            start = fields.Datetime.to_datetime(outage.started_at)
            end = (
                fields.Datetime.to_datetime(outage.ended_at)
                if outage.ended_at
                else now
            )
            assert start is not None
            assert end is not None

            clipped_start = max(start, period_start)
            clipped_end = min(end, now)

            if clipped_end <= clipped_start: continue

            duration = (clipped_end - clipped_start).total_seconds()
            total_downtime += duration

            if outage.ended_at:
                completed_count += 1
                durations.append(
                    (end - start).total_seconds()
                )

            # Split downtime across calendar days
            cursor = clipped_start
            while cursor < clipped_end:
                day_key = cursor.date().isoformat()
                next_day = (cursor + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                segment_end = min(next_day, clipped_end)

                if day_key in daily:
                    daily[day_key]["count"] += 1
                    daily[day_key]["downtime_seconds"] += int(
                        (segment_end - cursor).total_seconds()
                    )

                cursor = segment_end

        period_seconds = days * 24 * 60 * 60
        uptime_seconds = max(0, period_seconds - total_downtime)

        availability = max(
            0.0,
            (uptime_seconds / period_seconds) * 100,
        )

        # Mean Time To Recover
        mttr = (
            sum(durations) / len(durations)
            if durations
            else 0
        )

        # Mean Time Between Failures
        completed = self.search([
            ("ended_at", "!=", False),
            ("ended_at", "<=", now),
            ("started_at", "<", now),
        ], order="started_at asc")

        gaps = []
        previous_end = None

        for outage in completed:
            start = fields.Datetime.to_datetime(outage.started_at)
            end = fields.Datetime.to_datetime(outage.ended_at)
            assert start is not None
            assert end is not None

            if previous_end and start > previous_end:
                gaps.append((start - previous_end).total_seconds())

            previous_end = max(previous_end, end) if previous_end else end


        #* Build calendar rows.

        first_day = period_start.date()
        # Note: +1 for 0 index, -1 for monday
        leading_empty = (first_day.weekday()) % 7

        calendar = []

        # Empty cells before the first day.
        for index in range(leading_empty):
            calendar.append({
                "key": f"empty-{index}",
                "empty": True,
            })

        # Actual days.
        for day in daily.values():
            date_obj = fields.Date.from_string(day["date"])
            assert date_obj is not None

            calendar.append({
                "key": day["date"],
                "date": day["date"],
                "day": date_obj.day,
                "count": day["count"],
                "downtime_seconds": day["downtime_seconds"],
                "empty": False,
            })

        trailing_empty = (7 - (len(calendar) % 7)) % 7

        for index in range(trailing_empty):
            calendar.append({
                "key": f"trailing-empty-{index}",
                "empty": True,
            })

        calendar_rows = [
            calendar[index:index + 7]
            for index in range(0, len(calendar), 7)
        ]

        return {
            "period_days": days,
            "availability": round(availability, 5),
            "total_downtime_seconds": int(total_downtime),
            "outage_count": len(outages),
            "completed_count": completed_count,
            "mttr_seconds": int(mttr),
            "mtbf_seconds": int(
                sum(gaps) / len(gaps)
            ) if gaps else 0,
            "calendar": calendar_rows,
        }
