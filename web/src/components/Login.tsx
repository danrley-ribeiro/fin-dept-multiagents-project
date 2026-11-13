// Entrada no escritório (ADR-009): cada pessoa entra com a sua conta; o que ela pode fazer vem dos papéis dela.
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import { Alert, Avatar, Box, Button, Paper, Stack, TextField, Typography } from "@mui/material";
import { useState } from "react";
import { entrar, trocarSenha, type Saude, type Sessao } from "../api/sessao";

export function Login({ saude, aoEntrar, aviso }: { saude: Saude; aoEntrar: (s: Sessao) => void; aviso?: string }) {
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const enviar = async (e: React.FormEvent) => {
    e.preventDefault();
    setEnviando(true);
    setErro(null);  // a mensagem da tentativa anterior some enquanto a nova é conferida
    const r = await entrar(usuario.trim(), senha);
    setEnviando(false);
    if (r.sessao) aoEntrar(r.sessao);
    else { setErro(r.erro ?? "não foi possível entrar"); setSenha(""); }
  };

  return (
    <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 2 }}>
      <Paper component="form" onSubmit={enviar} aria-label="Entrar no escritório" sx={{ p: 4, width: "100%", maxWidth: 400 }}>
        <Stack spacing={2}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Avatar src="/sma-logo.svg" alt="SMA" variant="rounded" sx={{ width: 44, height: 44 }} />
            <Box>
              <Typography variant="h1" component="h1">SMA · Escritório de controladoria</Typography>
              <Typography variant="caption" color="text.secondary">Entre com a sua conta · versão {saude.versao}</Typography>
            </Box>
          </Stack>
          {aviso && <Alert severity="warning">{aviso}</Alert>}
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
