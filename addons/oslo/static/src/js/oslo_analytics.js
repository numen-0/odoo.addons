/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class OsloAnalytics extends Component {
    static template = "oslo.OsloAnalytics";

    setup() {
        this.state = useState({
            loading: true,
            days: Number(localStorage.getItem("oslo_reliability_days")) || 30,
            data: null,
        });

        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;

        try {
            this.state.data = await rpc(
                "/web/dataset/call_kw/oslo.outage/get_reliability_data",
                {
                    model: "oslo.outage",
                    method: "get_reliability_data",
                    args: [],
                    kwargs: { days: this.state.days },
                }
            );
        } finally {
            this.state.loading = false;
        }
    }

    async setPeriod(event) {
        this.state.days = Number(event.target.value);
        localStorage.setItem("oslo_reliability_days", this.state.days);
        await this.loadData();
    }

    formatDuration(seconds) {
        seconds = Math.floor(seconds || 0);

        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);

        if (days) return `${days}d ${hours}h`;
        if (hours) return `${hours}h ${minutes}m`;
        return `${minutes}m`;
    }

    formatDate(date) {
        return new Date(`${date}T12:00:00`).toLocaleDateString();
    }
}

registry.category("actions").add("oslo_analytics", OsloAnalytics);
