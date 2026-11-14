// Empresa ativa da sessão (IAM-09, ADR-012): cada empresa tem a sua simulação, os seus dados e a sua memória.
// O seletor só aparece para a conta com mais de uma empresa no escopo; quem entra sem empresa ativa escolhe antes.
import BusinessIcon from "@mui/icons-material/Business";
import {
  Alert, Box, Button, Chip, FormControl, InputLabel, List, ListItemButton, ListItemIcon, ListItemText, MenuItem, Paper,
  Select, Stack, Tooltip, Typography,
} from "@mui/material";
import type { EmpresasDaConta } from "../api/avancado";
import type { Sessao } from "../api/sessao";

/** Empresa em que a sessão está, quando o cadastro tem empresas. */
export function empresaAtiva(empresas: EmpresasDaConta | null, sessao: Sessao | null | undefined) {
  if (!empresas?.multiempresa || !sessao?.empresa) return null;
  return empresas.empresas.find((e) => e.id === sessao.empresa) ?? null;
}

/** No cabeçalho: com várias empresas, o seletor; com uma só, o nome dela (sem nada para trocar). */
export function SeletorEmpresa({ empresas, sessao, aoTrocar }: { empresas: EmpresasDaConta | null; sessao: Sessao;
  aoTrocar: (id: string) => void }) {
  const ativa = empresaAtiva(empresas, sessao);
  if (!empresas?.multiempresa || !ativa) return null;
  if (empresas.empresas.length < 2) {
    return (
      <Tooltip title="Empresa desta sessão (a sua conta tem acesso só a ela)">
        <Chip icon={<BusinessIcon />} variant="outlined" color="primary" aria-label="Empresa ativa" label={ativa.nome} />
      </Tooltip>
    );
  }
  return (
    <FormControl size="small" sx={{ minWidth: 200 }}>
      <InputLabel id="empresa-ativa">Empresa ativa</InputLabel>
      <Select labelId="empresa-ativa" label="Empresa ativa" value={ativa.id} onChange={(e) => aoTrocar(e.target.value)}
        renderValue={() => <Stack direction="row" spacing={0.75} alignItems="center"><BusinessIcon fontSize="small" color="primary" />
          <b>{ativa.nome}</b></Stack>}>
        {empresas.empresas.map((e) => (
          <MenuItem key={e.id} value={e.id}>{e.nome} <Typography component="span" variant="caption" color="text.secondary"
            sx={{ ml: 1 }}>{e.id} · porte {e.porte}</Typography></MenuItem>))}
      </Select>
    </FormControl>
  );
}

/** Entrada sem empresa ativa (conta com várias, ou escopo mudado): nada do escritório abre antes da escolha. */
export function EscolherEmpresa({ sessao, empresas, erro, aoEscolher, aoSair }: { sessao: Sessao; empresas: EmpresasDaConta;
  erro?: string | null; aoEscolher: (id: string) => void; aoSair: () => void }) {
  return (
    <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 2 }}>
      <Paper component="main" aria-label="Escolher a empresa" sx={{ p: 4, width: "100%", maxWidth: 460 }}>
        <Stack spacing={2}>
          <Typography variant="h2" component="h1">Em qual empresa você vai trabalhar?</Typography>
          <Typography variant="body2" color="text.secondary">
            {sessao.nome} ({sessao.usuario}): cada empresa tem os seus dados, a sua simulação e a sua memória. Dá para
            trocar depois, pelo seletor no cabeçalho.
          </Typography>
          {erro && <Alert severity="error" role="alert">{erro}</Alert>}
          {empresas.empresas.length ? (
            <List aria-label="Empresas da sua conta" disablePadding>
              {empresas.empresas.map((e, i) => (
                <ListItemButton key={e.id} autoFocus={i === 0} onClick={() => aoEscolher(e.id)} divider>
                  <ListItemIcon><BusinessIcon /></ListItemIcon>
                  <ListItemText primary={e.nome} secondary={`${e.id} · porte ${e.porte}`} />
                </ListItemButton>))}
            </List>
          ) : (
            <Alert severity="warning">A sua conta não tem acesso a nenhuma empresa. Procure o administrador de acesso
              (o escopo de empresas é definido no console de administração).</Alert>)}
          <Stack direction="row" justifyContent="flex-start"><Button onClick={aoSair}>Sair da conta</Button></Stack>
        </Stack>
      </Paper>
    </Box>
  );
}
