/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class OsloHome extends Component {
    static template = "oslo.OsloHome";

    setup() {
        this.state = useState({
            loading: true,
            outageId: null,
            isActive: false,
            startedAt: null,
            startedBy: null,
            lastOutageEndedAt: null,
        });

        onWillStart(async () => {
            await this.loadDashboard();
        });
    }

    async loadDashboard() {
        const data = await rpc(
            "/web/dataset/call_kw/oslo.outage/get_dashboard_data",
            {
                model: "oslo.outage",
                method: "get_dashboard_data",
                args: [],
                kwargs: {},
            }
        );

        this.state.outageId = data.id;
        this.state.isActive = data.is_active;
        this.state.startedAt = data.started_at;
        this.state.startedBy = data.started_by;
        this.state.lastOutageEndedAt = data.last_outage_ended_at;
        this.state.loading = false;
    }

    async startOutage() {
        await rpc(
            "/web/dataset/call_kw/oslo.outage/action_start_outage",
            {
                model: "oslo.outage",
                method: "action_start_outage",
                args: [],
                kwargs: {},
            }
        );

        await this.loadDashboard();
    }

    async endOutage() {
        if ( !this.state.isActive ) { return; }

        await rpc(
            "/web/dataset/call_kw/oslo.outage/action_end_outage",
            {
                model: "oslo.outage",
                method: "action_end_outage",
                args: [[this.state.outageId]],
                kwargs: {},
            }
        );

        await this.loadDashboard();
    }
}

registry.category("actions").add("oslo_home", OsloHome);
