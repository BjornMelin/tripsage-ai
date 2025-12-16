/**
 * @fileoverview Modal slice for UI store.
 */

import type { StateCreator } from "zustand";
import { useUiStore } from "./index";
import type { ModalSlice, ModalState, UiState } from "./types";

export const DEFAULT_MODAL_STATE: ModalState = {
  closeOnOverlayClick: true,
  component: null,
  isOpen: false,
  props: {},
  size: "md",
};

export const createModalSlice: StateCreator<UiState, [], [], ModalSlice> = (set) => ({
  closeModal: () => {
    set({ modal: DEFAULT_MODAL_STATE });
  },
  modal: DEFAULT_MODAL_STATE,

  openModal: (component, props = {}, options = {}) => {
    set({
      modal: {
        closeOnOverlayClick: options.closeOnOverlayClick ?? true,
        component,
        isOpen: true,
        props,
        size: options.size || "md",
      },
    });
  },

  updateModalProps: (props) => {
    set((state) => ({
      modal: {
        ...state.modal,
        props: {
          ...state.modal.props,
          ...props,
        },
      },
    }));
  },
});

// ===== SELECTOR HOOKS =====

/** Select whether the modal is open */
export const useModalOpen = () => useUiStore((s) => s.modal.isOpen);

/** Select the modal component */
export const useModalComponent = () => useUiStore((s) => s.modal.component);

/** Select the modal props */
export const useModalProps = () => useUiStore((s) => s.modal.props);

/** Select the modal size */
export const useModalSize = () => useUiStore((s) => s.modal.size);
