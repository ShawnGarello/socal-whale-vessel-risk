/** Minimal layer surface needed for deterministic owned-resource cleanup. */
export interface DestroyableLayer {
  destroy(): void;
}

export interface LayerMapLike<Layer> {
  remove(layer: Layer): void;
}

export interface LayerRefLike<Layer> {
  current: Layer | null;
}

/**
 * Releases only the layer owned by one effect execution.
 *
 * A stale async completion must not consult the ref to choose what to destroy:
 * a newer effect may already have installed its replacement there.
 */
export function releaseOwnedVsrLayer<Layer extends DestroyableLayer>(
  map: LayerMapLike<Layer>,
  ownedLayer: Layer | null,
  layerRef: LayerRefLike<Layer>,
): void {
  if (!ownedLayer) return;

  map.remove(ownedLayer);
  ownedLayer.destroy();
  if (layerRef.current === ownedLayer) layerRef.current = null;
}
