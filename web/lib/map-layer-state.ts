/**
 * Shared loading state for one operational map layer.
 *
 * Each layer tracks its own status so a failure in one cannot take the basemap
 * or another layer down with it. The reducer is deliberately free of any layer
 * identity: the message shown when the map itself never becomes ready is
 * supplied by the caller, because only the caller knows which layer it is.
 */
export type MapLayerStatus = "waiting" | "loading" | "ready" | "error";

export interface MapLayerState {
  readonly status: MapLayerStatus;
  readonly visible: boolean;
  readonly featureCount: number | null;
  readonly warning: string | null;
}

export type MapLayerAction =
  | { readonly type: "load-started" }
  | { readonly type: "load-succeeded"; readonly featureCount: number }
  | { readonly type: "load-failed"; readonly warning: string }
  | { readonly type: "map-unavailable"; readonly warning: string }
  | { readonly type: "visibility-changed"; readonly visible: boolean };

export const INITIAL_MAP_LAYER_STATE: MapLayerState = {
  status: "waiting",
  visible: true,
  featureCount: null,
  warning: null,
};

export function mapLayerReducer(
  state: MapLayerState,
  action: MapLayerAction,
): MapLayerState {
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
    case "map-unavailable":
      return {
        ...state,
        status: "error",
        featureCount: null,
        warning: action.warning,
      };
    case "visibility-changed":
      return { ...state, visible: action.visible };
  }
}
