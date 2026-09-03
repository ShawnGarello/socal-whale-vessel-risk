export type VsrLayerStatus = "waiting" | "loading" | "ready" | "error";

export interface VsrLayerState {
  readonly status: VsrLayerStatus;
  readonly visible: boolean;
  readonly featureCount: number | null;
  readonly warning: string | null;
}

export type VsrLayerAction =
  | { readonly type: "load-started" }
  | { readonly type: "load-succeeded"; readonly featureCount: number }
  | { readonly type: "load-failed"; readonly warning: string }
  | { readonly type: "map-unavailable" }
  | { readonly type: "visibility-changed"; readonly visible: boolean };

export const VSR_MAP_UNAVAILABLE_MESSAGE =
  "The 2026 California VSR zone is unavailable because the map could not be initialized.";

export const INITIAL_VSR_LAYER_STATE: VsrLayerState = {
  status: "waiting",
  visible: true,
  featureCount: null,
  warning: null,
};

export function vsrLayerReducer(
  state: VsrLayerState,
  action: VsrLayerAction,
): VsrLayerState {
  switch (action.type) {
    case "load-started":
      return { ...state, status: "loading", featureCount: null, warning: null };
    case "load-succeeded":
      return {
        ...state,
        status: "ready",
        featureCount: action.featureCount,
        warning: null,
      };
    case "load-failed":
      return {
        ...state,
        status: "error",
        featureCount: null,
        warning: action.warning,
      };
    case "map-unavailable":
      return {
        ...state,
        status: "error",
        featureCount: null,
        warning: VSR_MAP_UNAVAILABLE_MESSAGE,
      };
    case "visibility-changed":
      return { ...state, visible: action.visible };
  }
}
