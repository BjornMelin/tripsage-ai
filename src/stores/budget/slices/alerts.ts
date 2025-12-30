/**
 * @fileoverview Alerts slice for the budget store.
 */

import type { BudgetAlert } from "@schemas/budget";
import type { StateCreator } from "zustand";
import type { BudgetState, BudgetStoreDeps } from "../types";

type BudgetAlertsSlice = Pick<
  BudgetState,
  "alerts" | "addAlert" | "clearAlerts" | "markAlertAsRead" | "setAlerts"
>;

export const createBudgetAlertsSlice =
  (deps: BudgetStoreDeps): StateCreator<BudgetState, [], [], BudgetAlertsSlice> =>
  (set) => ({
    addAlert: (alert) =>
      set((state) => {
        const budgetId = alert.budgetId;
        const currentAlerts = state.alerts[budgetId] || [];

        const newAlert: BudgetAlert = {
          ...alert,
          createdAt: alert.createdAt || deps.nowIso(),
          id: alert.id || deps.generateId(),
          isRead: false,
        };

        return {
          alerts: {
            ...state.alerts,
            [budgetId]: [...currentAlerts, newAlert],
          },
        };
      }),

    alerts: {},

    clearAlerts: (budgetId) =>
      set((state) => {
        const newAlerts = { ...state.alerts };
        delete newAlerts[budgetId];

        return {
          alerts: newAlerts,
        };
      }),

    markAlertAsRead: (id, budgetId) =>
      set((state) => {
        const alerts = state.alerts[budgetId] || [];
        const alertIndex = alerts.findIndex((existing) => existing.id === id);

        if (alertIndex === -1) return state;

        const updatedAlerts = [...alerts];
        updatedAlerts[alertIndex] = {
          ...updatedAlerts[alertIndex],
          isRead: true,
        };

        return {
          alerts: {
            ...state.alerts,
            [budgetId]: updatedAlerts,
          },
        };
      }),

    setAlerts: (budgetId, alerts) =>
      set((state) => ({
        alerts: {
          ...state.alerts,
          [budgetId]: alerts,
        },
      })),
  });
