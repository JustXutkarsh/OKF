import "@testing-library/jest-dom/vitest";

if (typeof window !== "undefined") {
  if (!window.IntersectionObserver) {
    class MockIntersectionObserver {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    window.IntersectionObserver = MockIntersectionObserver as unknown as typeof IntersectionObserver;
  }

  if (!window.ResizeObserver) {
    class MockResizeObserver {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    window.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;
  }

  if (!window.DOMMatrixReadOnly) {
    class MockDOMMatrixReadOnly {
      m11 = 1; m12 = 0; m21 = 0; m22 = 1; m41 = 0; m42 = 0;
      a = 1; b = 0; c = 0; d = 1; e = 0; f = 0;
      transformPoint() { return { x: 0, y: 0, z: 0, w: 1 }; }
    }
    window.DOMMatrixReadOnly = MockDOMMatrixReadOnly as unknown as typeof DOMMatrixReadOnly;
    window.DOMMatrix = MockDOMMatrixReadOnly as unknown as typeof DOMMatrix;
  }

  if (typeof SVGElement !== "undefined" && !(SVGElement.prototype as unknown as { getBBox?: () => unknown }).getBBox) {
    (SVGElement.prototype as unknown as { getBBox: () => unknown }).getBBox = () => ({
      x: 0,
      y: 0,
      width: 0,
      height: 0,
      top: 0,
      right: 0,
      bottom: 0,
      left: 0,
      toJSON: () => "",
    });
  }
}
