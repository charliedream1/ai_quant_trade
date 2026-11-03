/** Fit only after a requested container transition has settled; ordinary evidence updates never fit. */
export function viewportFitter(
  element: HTMLElement,
  stableFrames: number,
  fit: () => unknown,
) {
  let frame = 0,
    pending = false,
    generation = 0,
    stable = 0,
    width = 0,
    height = 0;
  async function measure() {
    const active = generation;
    const rect = element.getBoundingClientRect();
    stable = rect.width === width && rect.height === height ? stable + 1 : 0;
    width = rect.width;
    height = rect.height;
    if (stable >= stableFrames && width && height) {
      await fit();
      if (active !== generation) return;
      const settled = element.getBoundingClientRect();
      if (settled.width !== width || settled.height !== height) {
        request();
        return;
      }
      pending = false;
      element.dataset.fitPending = "false";
    } else frame = requestAnimationFrame(measure);
  }
  function request() {
    cancelAnimationFrame(frame);
    generation += 1;
    pending = true;
    stable = 0;
    element.dataset.fitPending = "true";
    frame = requestAnimationFrame(measure);
  }
  const observer = new ResizeObserver(() => {
    if (pending) request();
  });
  observer.observe(element);
  return {
    request,
    destroy() {
      generation += 1;
      cancelAnimationFrame(frame);
      observer.disconnect();
      pending = false;
    },
  };
}
