// Toast store - short feedback messages after an action (UI rule "Feedback", SPEC §3.4)

import { create } from "zustand";

export type ToastTone = "success" | "error" | "info";

export type Toast = { id: number; message: string; tone: ToastTone };

interface ToastState {
  toasts: Toast[];
  push: (message: string, tone?: ToastTone) => void;
  dismiss: (id: number) => void;
}

let nextId = 1;

export const useToast = create<ToastState>()((set, get) => ({
  toasts: [],
  push: (message, tone = "success") => {
    const id = nextId++;
    set({ toasts: [...get().toasts, { id, message, tone }] });
    window.setTimeout(() => get().dismiss(id), 4000);
  },
  dismiss: (id) => set({ toasts: get().toasts.filter((toast) => toast.id !== id) }),
}));

export const toast = {
  success: (message: string) => useToast.getState().push(message, "success"),
  error: (message: string) => useToast.getState().push(message, "error"),
  info: (message: string) => useToast.getState().push(message, "info"),
};
