export const appVariant = String(import.meta.env.VITE_APP_VARIANT || "prod").toLowerCase();
export const isDevVariant = appVariant === "dev";
export const isProdVariant = !isDevVariant;
