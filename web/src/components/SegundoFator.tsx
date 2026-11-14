// Meu segundo fator (IAM-08, ADR-012): a própria pessoa ativa, confere, troca os códigos de recuperação e desativa.
// O segredo e os códigos de recuperação vêm do servidor uma única vez; saem da memória da página assim que a pessoa
// confirma que os guardou. Quando a política do cadastro exige o segundo fator, esta é a única tela disponível.
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import {
  Alert, Box, Button, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, Paper, Stack, TextField,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useState } from "react";
import {
  confirmarSegundoFator, desativarSegundoFator, iniciarSegundoFator, renovarCodigosDeRecuperacao, situacaoSegundoFator,
  type SituacaoSegundoFator,
} from "../api/avancado";
import type { Sessao } from "../api/sessao";

type Fase = "resumo" | "cadastro" | "codigos" | "renovar" | "desativar";

async function copiar(texto: string): Promise<boolean> {
  try { await navigator.clipboard.writeText(texto); return true; } catch { return false; }
}

function CampoCodigo({ rotulo, valor, aoMudar, ajuda }: { rotulo: string; valor: string; aoMudar: (v: string) => void;
  ajuda: string }) {
  return (
    <TextField label={rotulo} value={valor} onChange={(e) => aoMudar(e.target.value)} autoFocus required fullWidth
      autoComplete="one-time-code" helperText={ajuda}
      inputProps={{ "aria-label": rotulo, maxLength: 32, spellCheck: false, autoCapitalize: "none", autoCorrect: "off" }} />
  );
}

interface PainelProps {
  sessao: Sessao;
  /** A política exige e a conta ainda não tem: a pessoa só sai daqui com o segundo fator ativo (ou saindo da conta). */
  obrigatorio?: boolean;
  /** Depois de ativar, desativar ou trocar os códigos: quem chamou relê a sessão. */
  aoMudar: () => void;
  /** Há algo na tela que só aparece uma vez: o diálogo não fecha por fora enquanto isso. */
  aoReter?: (retido: boolean) => void;
}

export function PainelSegundoFator({ sessao, obrigatorio, aoMudar, aoReter }: PainelProps) {
  const [situacao, setSituacao] = useState<SituacaoSegundoFator | null>(null);
  const [fase, setFase] = useState<Fase>("resumo");
  const [cadastro, setCadastro] = useState<{ segredo: string; uri: string } | null>(null);
  const [codigos, setCodigos] = useState<string[]>([]);
  const [codigo, setCodigo] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [nota, setNota] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const carregar = useCallback(async () => {
    const r = await situacaoSegundoFator();
    if (r.dados) setSituacao(r.dados); else if (r.status !== 401) setErro(r.erro ?? "não foi possível consultar o segundo fator");
  }, []);
  useEffect(() => { carregar(); }, [carregar]);
  useEffect(() => { aoReter?.(fase === "codigos"); }, [fase, aoReter]);

  const ir = (nova: Fase) => { setFase(nova); setCodigo(""); setErro(null); setNota(null); };
  const executar = async <T,>(acao: () => Promise<{ dados?: T; erro?: string }>): Promise<T | null> => {
    setOcupado(true);
    setErro(null);
    const r = await acao();
    setOcupado(false);
    if (r.dados === undefined) { setErro(r.erro ?? "não foi possível concluir"); setCodigo(""); return null; }
    return r.dados;
  };

  const ativar = async () => {
    const d = await executar(iniciarSegundoFator);
    if (d) { setCadastro(d); ir("cadastro"); }
  };
  const confirmar = async (e: React.FormEvent) => {
    e.preventDefault();
    const d = await executar(() => confirmarSegundoFator(codigo.trim()));
    if (d) { setCadastro(null); setCodigos(d.codigos_recuperacao); ir("codigos"); carregar(); }
  };
  const renovar = async (e: React.FormEvent) => {
    e.preventDefault();
    const d = await executar(() => renovarCodigosDeRecuperacao(codigo.trim()));
    if (d) { setCodigos(d.codigos_recuperacao); ir("codigos"); carregar(); }
  };
  const desativar = async (e: React.FormEvent) => {
    e.preventDefault();
    const d = await executar(() => desativarSegundoFator(codigo.trim()));
    if (d) { ir("resumo"); setNota("Segundo fator desativado: a entrada volta a pedir só usuário e senha."); await carregar(); aoMudar(); }
  };
  const guardei = () => { setCodigos([]); ir("resumo"); aoMudar(); };

  if (!situacao) {
    return erro ? <Alert severity="error" role="alert">{erro}</Alert>
      : <Stack alignItems="center" sx={{ py: 3 }}><CircularProgress size={28} aria-label="Consultando o segundo fator" /></Stack>;
  }

  return (
    <Stack spacing={2} aria-label="Meu segundo fator" component="section">
      {obrigatorio && fase !== "codigos" && (
        <Alert severity="info">A política do cadastro exige o segundo fator para a conta <b>{sessao.usuario}</b>.
          Ative-o para continuar: até lá, o escritório fica indisponível.</Alert>)}

      {fase === "resumo" && (<>
        <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap">
          <Typography variant="body1">Situação:</Typography>
          <Chip aria-label="Situação do segundo fator" color={situacao.ativo ? "success" : "default"}
            variant={situacao.ativo ? "filled" : "outlined"} label={situacao.ativo ? "ativo" : "não ativado"} />
          {situacao.exigido && <Chip size="small" variant="outlined" color="warning" label="exigido pela política do cadastro" />}
        </Stack>
        {situacao.ativo ? (
          <Typography variant="body2" color="text.secondary">
            {situacao.desde ? `Ativo desde ${new Date(situacao.desde * 1000).toLocaleString("pt-BR")}. ` : ""}
            A entrada pede a senha e, depois, o código do aplicativo autenticador.{" "}
            <span aria-label="Códigos de recuperação restantes">{situacao.codigos_restantes === 1
              ? "Resta 1 código de recuperação." : `Restam ${situacao.codigos_restantes} códigos de recuperação.`}</span>
          </Typography>
        ) : (
          <Typography variant="body2" color="text.secondary">
            Com o segundo fator, a senha sozinha não abre a sua conta: a entrada pede também um código de 6 dígitos
            gerado por um aplicativo autenticador no seu aparelho (TOTP, RFC 6238).
          </Typography>)}
        {nota && <Alert severity="success">{nota}</Alert>}
        {erro && <Alert severity="error" role="alert">{erro}</Alert>}
        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
          {!situacao.ativo && <Button variant="contained" onClick={ativar} disabled={ocupado}>Ativar o segundo fator</Button>}
          {situacao.ativo && <Button variant="outlined" onClick={() => ir("renovar")}>Gerar novos códigos de recuperação</Button>}
          {situacao.ativo && <Button variant="outlined" color="error" onClick={() => ir("desativar")}>Desativar</Button>}
          {obrigatorio && situacao.ativo && <Button variant="contained" onClick={aoMudar}>Continuar</Button>}
        </Stack>
      </>)}

      {fase === "cadastro" && cadastro && (
        <Stack component="form" spacing={2} onSubmit={confirmar} aria-label="Cadastrar o aplicativo autenticador">
          <Alert severity="warning">O segredo abaixo aparece <b>só agora</b>. Cadastre-o no aplicativo autenticador antes de
            sair desta tela.</Alert>
          <Box>
            <Typography variant="caption" color="text.secondary">Segredo (digite no aplicativo, opção “chave de
              configuração”, tipo “baseado em tempo”)</Typography>
            <Stack direction="row" spacing={1} alignItems="center">
              <Box component="code" aria-label="Segredo do segundo fator" sx={{ fontSize: 16, letterSpacing: 1.5,
                wordBreak: "break-all", userSelect: "all" }}>{cadastro.segredo}</Box>
              <Button size="small" startIcon={<ContentCopyIcon fontSize="small" />}
                onClick={async () => setNota(await copiar(cadastro.segredo) ? "Segredo copiado." : "Não foi possível copiar: selecione o texto.")}>
                Copiar</Button>
            </Stack>
          </Box>
          <TextField label="Endereço otpauth:// (para aplicativos que aceitam colar o endereço)" value={cadastro.uri}
            fullWidth multiline size="small" InputProps={{ readOnly: true }}
            inputProps={{ "aria-label": "Endereço otpauth", spellCheck: false }} />
          {nota && <Typography variant="caption" color="text.secondary" role="status">{nota}</Typography>}
          <CampoCodigo rotulo="Primeiro código do aplicativo" valor={codigo} aoMudar={setCodigo}
            ajuda="Os 6 dígitos que o aplicativo mostra agora: é o que confirma o cadastro." />
          {erro && <Alert severity="error" role="alert">{erro}</Alert>}
          <Stack direction="row" spacing={1} justifyContent="flex-end">
            <Button onClick={() => { setCadastro(null); ir("resumo"); }}>Cancelar</Button>
            <Button type="submit" variant="contained" disabled={ocupado || !codigo.trim()}>Confirmar e ativar</Button>
          </Stack>
        </Stack>)}

      {fase === "codigos" && (<>
        <Alert severity="warning">Guarde estes códigos de recuperação <b>agora</b>, fora deste computador: eles não serão
          mostrados de novo. Cada um vale uma única vez e entra no lugar do código do aplicativo.</Alert>
        <Box component="ul" aria-label="Códigos de recuperação" sx={{ m: 0, pl: 0, listStyle: "none", display: "grid",
          gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 0.75 }}>
          {codigos.map((c) => <Box component="li" key={c}><Box component="code" sx={{ fontSize: 15, userSelect: "all" }}>{c}</Box></Box>)}
        </Box>
        {nota && <Typography variant="caption" color="text.secondary" role="status">{nota}</Typography>}
        <Stack direction="row" spacing={1} justifyContent="flex-end">
          <Button startIcon={<ContentCopyIcon fontSize="small" />}
            onClick={async () => setNota(await copiar(codigos.join("\n")) ? "Códigos copiados." : "Não foi possível copiar: selecione o texto.")}>
            Copiar todos</Button>
          <Button variant="contained" onClick={guardei}>Já guardei os códigos</Button>
        </Stack>
      </>)}

      {fase === "renovar" && (
        <Stack component="form" spacing={2} onSubmit={renovar} aria-label="Gerar novos códigos de recuperação">
          <Typography variant="body2">Os códigos de recuperação atuais deixam de valer e dez novos são mostrados uma
            única vez.</Typography>
          <CampoCodigo rotulo="Código atual" valor={codigo} aoMudar={setCodigo}
            ajuda="6 dígitos do aplicativo autenticador ou um código de recuperação ainda não usado." />
          {erro && <Alert severity="error" role="alert">{erro}</Alert>}
          <Stack direction="row" spacing={1} justifyContent="flex-end">
            <Button onClick={() => ir("resumo")}>Cancelar</Button>
            <Button type="submit" variant="contained" disabled={ocupado || !codigo.trim()}>Gerar novos códigos</Button>
          </Stack>
        </Stack>)}

      {fase === "desativar" && (
        <Stack component="form" spacing={2} onSubmit={desativar} aria-label="Desativar o segundo fator">
          <Alert severity="warning">Sem o segundo fator, quem souber a sua senha entra na sua conta.
            {situacao.exigido && " A política do cadastro exige o segundo fator para a sua conta: depois de desativar, "
              + "você só poderá usar o escritório ativando-o de novo."}</Alert>
          <CampoCodigo rotulo="Código atual" valor={codigo} aoMudar={setCodigo}
            ajuda="Confirme com os 6 dígitos do aplicativo autenticador ou com um código de recuperação." />
          {erro && <Alert severity="error" role="alert">{erro}</Alert>}
          <Stack direction="row" spacing={1} justifyContent="flex-end">
            <Button onClick={() => ir("resumo")}>Cancelar</Button>
            <Button type="submit" variant="contained" color="error" disabled={ocupado || !codigo.trim()}>
              Desativar o segundo fator</Button>
          </Stack>
        </Stack>)}
    </Stack>
  );
}

/** Pelo menu da conta: a pessoa cuida do próprio segundo fator sem sair do escritório. */
export function SegundoFatorDialog({ aberto, sessao, aoFechar, aoMudar }: { aberto: boolean; sessao: Sessao;
  aoFechar: () => void; aoMudar: () => void }) {
  const [retido, setRetido] = useState(false);
  return (
    <Dialog open={aberto} onClose={() => { if (!retido) aoFechar(); }} maxWidth="sm" fullWidth
      aria-labelledby="titulo-segundo-fator">
      <DialogTitle id="titulo-segundo-fator">Meu segundo fator · {sessao.usuario}</DialogTitle>
      <DialogContent dividers>
        {aberto && <PainelSegundoFator sessao={sessao} aoMudar={aoMudar} aoReter={setRetido} />}
      </DialogContent>
      <DialogActions><Button onClick={aoFechar} disabled={retido}>Fechar</Button></DialogActions>
    </Dialog>
  );
}

/** A política do cadastro exige o segundo fator e a conta ainda não tem: tela inteira, como a da senha temporária. */
export function SegundoFatorObrigatorio({ sessao, aoConcluir, aoSair }: { sessao: Sessao; aoConcluir: () => void;
  aoSair: () => void }) {
  return (
    <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 2 }}>
      <Paper component="main" aria-label="Ativar o segundo fator" sx={{ p: 4, width: "100%", maxWidth: 560 }}>
        <Stack spacing={2}>
          <Typography variant="h2" component="h1">Ative o segundo fator de {sessao.usuario}</Typography>
          <PainelSegundoFator sessao={sessao} obrigatorio aoMudar={aoConcluir} />
          <Stack direction="row" justifyContent="flex-start">
            <Button onClick={aoSair}>Sair da conta</Button>
          </Stack>
        </Stack>
      </Paper>
    </Box>
  );
}
