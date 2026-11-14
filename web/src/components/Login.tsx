// Entrada no escritório (ADR-009): cada pessoa entra com a sua conta; o que ela pode fazer vem dos papéis dela.
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import { Alert, Avatar, Box, Button, Paper, Stack, TextField, Typography } from "@mui/material";
import { useCallback, useEffect, useRef, useState } from "react";
import { confirmarCodigo, entrar, trocarSenha, type Saude, type SegundoFatorPendente, type Sessao } from "../api/sessao";

const SEGUNDOS = (n: number) => `${Math.floor(n / 60)}:${String(n % 60).padStart(2, "0")}`;

/** Entrada em dois passos (IAM-08): usuário e senha; com o segundo fator ativo, o código do aplicativo autenticador
 *  ou um código de recuperação. O prazo e o limite de tentativas são do servidor; quando acabam, volta ao início. */
export function Login({ saude, aoEntrar, aviso }: { saude: Saude; aoEntrar: (s: Sessao) => void; aviso?: string }) {
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [pendente, setPendente] = useState<SegundoFatorPendente | null>(null);
  const [codigo, setCodigo] = useState("");
  const [nota, setNota] = useState<string | null>(null); // por que a pessoa voltou ao primeiro passo
  const [restam, setRestam] = useState(0); // segundos da pré-sessão
  const campoCodigo = useRef<HTMLInputElement>(null);

  const voltar = useCallback((motivo: string | null) => {
    setPendente(null);
    setCodigo("");
    setSenha("");
    setErro(null);
    setNota(motivo);
  }, []);

  useEffect(() => {
    if (!pendente) return;
    const conferir = () => {
      const segundos = Math.min(300, Math.ceil(pendente.expiraEm - Date.now() / 1000));
      setRestam(Math.max(0, segundos));
      if (segundos <= 0) voltar("O tempo para informar o código acabou. Entre de novo com usuário e senha.");
    };
    conferir();
    const t = setInterval(conferir, 1000);
    return () => clearInterval(t);
  }, [pendente, voltar]);

  const enviar = async (e: React.FormEvent) => {
    e.preventDefault();
    setEnviando(true);
    setErro(null);  // a mensagem da tentativa anterior some enquanto a nova é conferida
    setNota(null);
    const r = await entrar(usuario.trim(), senha);
    setEnviando(false);
    if (r.sessao) aoEntrar(r.sessao);
    else if (r.segundoFator) { setSenha(""); setCodigo(""); setPendente(r.segundoFator); }
    else { setErro(r.erro ?? "não foi possível entrar"); setSenha(""); }
  };

  const enviarCodigo = async (e: React.FormEvent) => {
    e.preventDefault();
    setEnviando(true);
    setErro(null);
    const r = await confirmarCodigo(codigo.trim());
    setEnviando(false);
    if (r.sessao) { aoEntrar(r.sessao); return; }
    if (r.encerrada) {
      voltar("O prazo ou as tentativas para informar o código acabaram. Entre de novo com usuário e senha.");
      return;
    }
    // o motivo exato (código errado, repetido, fora da janela, recuperação já usada) fica só na trilha do servidor
    setErro(`Código inválido.${r.tentativasRestantes !== undefined ? ` ${r.tentativasRestantes === 1
      ? "Resta 1 tentativa" : `Restam ${r.tentativasRestantes} tentativas`}.` : ""}`);
    setCodigo("");
    campoCodigo.current?.focus();
  };

  const cabecalho = (legenda: string) => (
    <Stack direction="row" spacing={1.5} alignItems="center">
      <Avatar src="/sma-logo.svg" alt="SMA" variant="rounded" sx={{ width: 44, height: 44 }} />
      <Box>
        <Typography variant="h1" component="h1">SMA · Escritório de controladoria</Typography>
        <Typography variant="caption" color="text.secondary">{legenda} · versão {saude.versao}</Typography>
      </Box>
    </Stack>
  );

  if (pendente) {
    return (
      <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 2 }}>
        <Paper component="form" onSubmit={enviarCodigo} aria-label="Confirmar o segundo fator"
          sx={{ p: 4, width: "100%", maxWidth: 400 }}>
          <Stack spacing={2}>
            {cabecalho("Segundo passo da entrada")}
            <Typography variant="body2">A senha de <b>{usuario.trim()}</b> confere. Falta o segundo fator.</Typography>
            <TextField label="Código de verificação" value={codigo} onChange={(e) => setCodigo(e.target.value)} autoFocus
              required autoComplete="one-time-code" inputRef={campoCodigo}
              helperText="6 dígitos do aplicativo autenticador ou um código de recuperação"
              inputProps={{ "aria-label": "Código de verificação", maxLength: 32, spellCheck: false,
                autoCapitalize: "none", autoCorrect: "off" }} />
            {erro && <Alert severity="error" role="alert">{erro}</Alert>}
            <Typography variant="caption" color="text.secondary" aria-label="Prazo do código">
              Este passo expira em {SEGUNDOS(restam)}; depois é preciso entrar de novo.</Typography>
            <Stack direction="row" spacing={1} justifyContent="space-between">
              <Button onClick={() => voltar(null)}>Voltar</Button>
              <Button type="submit" variant="contained" startIcon={<LockOutlinedIcon />} disabled={enviando || !codigo.trim()}>
                Confirmar código</Button>
            </Stack>
          </Stack>
        </Paper>
      </Box>
    );
  }

  return (
    <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 2 }}>
      <Paper component="form" onSubmit={enviar} aria-label="Entrar no escritório" sx={{ p: 4, width: "100%", maxWidth: 400 }}>
        <Stack spacing={2}>
          {cabecalho("Entre com a sua conta")}
          {aviso && !nota && <Alert severity="warning">{aviso}</Alert>}
          {nota && <Alert severity="warning">{nota}</Alert>}
          {!saude.acesso.integro && (
            <Alert severity="error">O cadastro de acesso está comprometido (IAM-07): ninguém entra até o administrador
              restaurá-lo.</Alert>)}
          {saude.acesso.sem_contas && (
            <Alert severity="info">Ainda não há contas. Crie o administrador com
              <code> python -m fin_mas acesso iniciar</code> ou suba o servidor com <code>--demo</code>.</Alert>)}
          <TextField label="Usuário" value={usuario} onChange={(e) => setUsuario(e.target.value)} autoFocus required
            autoComplete="username" inputProps={{ "aria-label": "Usuário" }} />
          <TextField label="Senha" type="password" value={senha} onChange={(e) => setSenha(e.target.value)} required
            autoComplete="current-password" inputProps={{ "aria-label": "Senha" }} />
          {erro && <Alert severity="error" role="alert">{erro}</Alert>}
          <Button type="submit" variant="contained" startIcon={<LockOutlinedIcon />} disabled={enviando || !usuario || !senha}>
            Entrar</Button>
        </Stack>
      </Paper>
    </Box>
  );
}

/** Senha temporária (definida pelo administrador): a pessoa troca antes de usar o escritório (IAM-02). */
export function TrocarSenha({ sessao, obrigatoria, aoConcluir, aoCancelar }: { sessao: Sessao; obrigatoria: boolean;
  aoConcluir: () => void; aoCancelar?: () => void }) {
  const [atual, setAtual] = useState("");
  const [nova, setNova] = useState("");
  const [repetir, setRepetir] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const enviar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (nova !== repetir) { setErro("as senhas novas não conferem"); return; }
    const falha = await trocarSenha(atual, nova);
    if (falha) setErro(falha); else aoConcluir();
  };
  return (
    <Box sx={{ minHeight: obrigatoria ? "100vh" : undefined, display: "grid", placeItems: "center", p: 2 }}>
      <Paper component="form" onSubmit={enviar} aria-label="Trocar senha" sx={{ p: 4, width: "100%", maxWidth: 420 }}>
        <Stack spacing={2}>
          <Typography variant="h2" component="h2">Trocar a senha de {sessao.usuario}</Typography>
          {obrigatoria && <Alert severity="info">A sua senha é temporária. Defina uma nova para continuar.</Alert>}
          <TextField label="Senha atual" type="password" value={atual} onChange={(e) => setAtual(e.target.value)} required
            autoComplete="current-password" />
          <TextField label="Senha nova" type="password" value={nova} onChange={(e) => setNova(e.target.value)} required
            autoComplete="new-password" helperText="No mínimo 12 caracteres, sem o nome de usuário." />
          <TextField label="Repita a senha nova" type="password" value={repetir} onChange={(e) => setRepetir(e.target.value)}
            required autoComplete="new-password" />
          {erro && <Alert severity="error" role="alert">{erro}</Alert>}
          <Stack direction="row" spacing={1} justifyContent="flex-end">
            {aoCancelar && <Button onClick={aoCancelar}>Cancelar</Button>}
            <Button type="submit" variant="contained" disabled={!atual || !nova || !repetir}>Salvar senha</Button>
          </Stack>
        </Stack>
      </Paper>
    </Box>
  );
}
