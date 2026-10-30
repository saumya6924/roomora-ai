// Temporary page script for panels that have not been ported yet: guard + shell only.
import { requireRole } from "../core/auth.js";
import { initDashboard } from "../core/dashboard.js";

const user = await requireRole(document.body.dataset.roles.split(","));
initDashboard(user);
