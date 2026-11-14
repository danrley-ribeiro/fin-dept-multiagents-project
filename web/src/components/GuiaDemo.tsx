// Demonstração guiada: um roteiro opcional sobre o dashboard ao vivo. Fica desligada por padrão, abre pelo botão
// “Demonstração guiada” e fecha a qualquer momento; nada no escritório depende dela. Os passos vêm de
// `demo/roteiro.ts`; aqui só há a moldura: mostrar o passo, conferir as permissões de quem está logado e enviar os
// mesmos comandos da barra de controles (o servidor confere cada um de novo).
import CloseIcon from "@mui/icons-material/Close";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import SlideshowIcon from "@mui/icons-material/Slideshow";
import { Box, Button, Chip, IconButton, Link, Paper, Stack, Tooltip, Typography } from "@mui/material";
import { useState } from "react";
import { pode, type Sessao } from "../api/sessao";
import { ROTEIRO, type AcaoDemo, type PassoDemo } from "../demo/roteiro";
import type { Controle } from "../types";

const PAPEL_DA_PERMISSAO: Record<string, string> = {
  "PERM-SIM-OPERAR": "operador", "PERM-AGT-ENERGIA": "operador", "PERM-MOD-CONFIG": "aprovador (controller)",
};

/** Comandos do passo para esta conta e o motivo, se ela não puder dispará-los. */
export function prepararAcao(acao: AcaoDemo, sessao: Sessao | null, controle: Controle | null) {
  const faltam = acao.permissoes.filter((p) => !pode(sessao, p));
  const motivo = faltam.length ? `Sua conta não tem o papel de ${[...new Set(faltam.map((p) => PAPEL_DA_PERMISSAO[p] ?? p))].join(" e ")
  } (${faltam.join(", ")}).` : null;
  // mudar o nível de cognição é ajuste de modelo (PERM-MOD-CONFIG): sem a permissão, o passo roda no nível atual
  const nivel = acao.cognicao?.nivel;
  const incluir = !!nivel && (controle?.cognicao === nivel || pode(sessao, "PERM-MOD-CONFIG"));
  const comandos = acao.comandos.map((c) => (c.tipo === "reiniciar" && incluir ? { ...c, cognicao: nivel } : c));
  return { comandos, motivo };
}

export function GuiaDemo({ sessao, controle, enviar, aoIrPara, aoFechar, passos = ROTEIRO }: {
  sessao: Sessao | null; controle: Controle | null;
  /** Envia um comando ao servidor; devolve o erro em texto, ou null. */
  enviar: (c: Record<string, unknown>) => Promise<string | null>;
  /** Leva o dashboard à aba, ao agente e ao filtro do passo. */
  aoIrPara: (passo: PassoDemo) => void;
  aoFechar: () => void;
  passos?: PassoDemo[];
}) {
  const [indice, setIndice] = useState(0);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState<{ passo: string; erro: string | null } | null>(null);
  const passo = passos[indice];
  const acao = passo.acao;
  const pronta = acao ? prepararAcao(acao, sessao, controle) : null;

  const executar = async () => {
    if (!acao || !pronta || pronta.motivo) return;
    setEnviando(true);
    let erro: string | null = null;
    for (const c of pronta.comandos) {
      erro = await enviar(c);
      if (erro) break;
    }
    setEnviando(false);
    setResultado({ passo: passo.id, erro });
    if (!erro) aoIrPara(passo);
  };
  const ir = (novo: number) => { setIndice(novo); setResultado(null); };

  const feito = resultado?.passo === passo.id ? resultado : null;
  const nivelExigido = acao?.cognicao?.obrigatoria ? acao.cognicao.nivel : null;
  const situacao = !feito ? null
    : feito.erro ? `Não foi possível: ${feito.erro}`
    : !acao?.comandos.length ? "Aberto."
    : `Em execução: cenário ${controle?.cenario ?? "…"} · cognição ${controle?.cognicao ?? "…"}.${
      nivelExigido && controle?.cognicao && controle.cognicao !== nivelExigido
        ? ` Este passo precisa do nível “${nivelExigido}”: quem tem o papel de aprovador muda o nível em “Agentes e LLM”.` : ""}`;

  return (
    <Paper component="aside" aria-label="Demonstração guiada" sx={{ maxWidth: 1688, mx: "auto", mt: 2, p: 2,
      borderLeft: 4, borderLeftColor: "primary.main", width: "calc(100% - 32px)" }}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
        <SlideshowIcon color="primary" fontSize="small" />
        <Typography variant="h2" component="h2">Demonstração guiada</Typography>
        <Chip size="small" variant="outlined" aria-label="Passo atual" label={`Passo ${indice + 1} de ${passos.length}`} />
        <Typography variant="caption" color="text.secondary" sx={{ display: { xs: "none", md: "block" } }}>
          Opcional: os botões enviam os mesmos comandos da barra de controles, com as permissões da sua conta.</Typography>
        <Box sx={{ flex: 1 }} />
        <Tooltip title="Fechar a demonstração (o escritório continua como está)">
          <IconButton size="small" aria-label="Fechar a demonstração guiada" onClick={aoFechar}><CloseIcon fontSize="small" /></IconButton>
        </Tooltip>
      </Stack>
      <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems={{ md: "flex-start" }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="h3" component="h3">{indice + 1}. {passo.titulo}</Typography>
          <Typography variant="body2" sx={{ mt: 0.5 }}>{passo.resumo}</Typography>
          <Box component="ol" aria-label="O que observar" sx={{ m: 0, mt: 0.75, pl: 2.5, fontSize: 14, color: "text.secondary" }}>
            {passo.observar.map((o) => <li key={o}>{o}</li>)}
          </Box>
          {passo.link && (
            <Link href={passo.link.href} target="_blank" rel="noopener noreferrer" variant="body2"
              sx={{ display: "inline-flex", alignItems: "center", gap: 0.5, mt: 0.75 }}>
              {passo.link.rotulo}<OpenInNewIcon sx={{ fontSize: 14 }} /></Link>)}
        </Box>
        <Stack spacing={1} sx={{ width: { xs: "100%", md: 320 }, flexShrink: 0 }}>
          {acao && pronta && (
            <Tooltip title={pronta.motivo ?? ""}>
              <span><Button fullWidth variant="contained" disabled={!!pronta.motivo || enviando} onClick={executar}>
                {acao.rotulo}</Button></span>
            </Tooltip>)}
          {pronta?.motivo && <Typography variant="caption" color="warning.main" aria-label="Por que o passo está indisponível">
            {pronta.motivo} Você pode acompanhar o passo quando outra pessoa o disparar.</Typography>}
          {situacao && <Typography variant="caption" role="status" aria-label="Situação do passo"
            color={feito?.erro ? "error.main" : "text.secondary"}>{situacao}</Typography>}
          <Stack direction="row" justifyContent="space-between">
            <Button size="small" onClick={() => ir(indice - 1)} disabled={indice === 0}>Anterior</Button>
            <Button size="small" onClick={() => ir(indice + 1)} disabled={indice === passos.length - 1}>Próximo</Button>
          </Stack>
        </Stack>
      </Stack>
    </Paper>
  );
}
