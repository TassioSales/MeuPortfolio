type ToastType = "success" | "error" | "info";

function show(message: string, type: ToastType, duration = 3500): void {
  if (typeof document === "undefined") return;

  const el = document.createElement("div");
  const colors = {
    success: "bg-emerald-500/90",
    error: "bg-red-500/90",
    info: "bg-blue-500/90",
  };

  el.className = [
    "fixed bottom-6 right-6 z-[9999] px-4 py-3 rounded-xl text-white text-sm font-medium shadow-xl",
    "transition-all duration-300 translate-y-2 opacity-0",
    colors[type],
  ].join(" ");
  el.textContent = message;
  document.body.appendChild(el);

  requestAnimationFrame(() => {
    el.classList.remove("translate-y-2", "opacity-0");
    el.classList.add("translate-y-0", "opacity-100");
  });

  setTimeout(() => {
    el.classList.add("translate-y-2", "opacity-0");
    setTimeout(() => el.remove(), 300);
  }, duration);
}

export const toast = {
  success: (msg: string) => show(msg, "success"),
  error: (msg: string) => show(msg, "error"),
  info: (msg: string) => show(msg, "info"),
};
