// Mesma regra da POL-04 do SVC-POL (src/fin_mas/services/politica.py, `_justificativa_valida`):
// pelo menos MIN_JUSTIFICATIVA caracteres e duas palavras distintas de 3 letras ou mais.
// O servidor continua sendo quem decide; aqui ela só evita habilitar o waiver com texto que será recusado.
export const MIN_JUSTIFICATIVA = 10;

export function justificativaValida(texto: string): boolean {
  const palavras = new Set((texto.match(/\p{L}{3,}/gu) ?? []).map((p) => p.toLowerCase()));
  return texto.trim().length >= MIN_JUSTIFICATIVA && palavras.size >= 2;
}
