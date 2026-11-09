// Declaraciones de módulos para archivos de imagen estáticos.
// Vite los procesa y retorna la URL del asset como string en runtime.
interface ImportMeta {
  readonly env: { readonly VITE_FRESH_INSTALL?: string };
}

declare module "*.jpg" {
  const src: string;
  export default src;
}

declare module "*.jpeg" {
  const src: string;
  export default src;
}

declare module "*.png" {
  const src: string;
  export default src;
}

declare module "*.svg" {
  const src: string;
  export default src;
}

declare module "*.webp" {
  const src: string;
  export default src;
}

declare module "*.gif" {
  const src: string;
  export default src;
}
