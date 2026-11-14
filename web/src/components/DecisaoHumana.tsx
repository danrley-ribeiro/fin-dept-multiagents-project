// O aprovador humano decide sobre o veto do AG-CIN no Approval Gate (PROT-APR): corrigir, waiver ou bloquear.
// A decisão cita o ticket do SVC-POL; o barramento a recusa se não for do aprovador designado (DSM3).
import GavelIcon from "@mui/icons-material/Gavel";
import {
  Alert, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, List, ListItem, ListItemText, Stack,
  TextField, Typography,
} from "@mui/material";
import { useState } from "react";
import { justificativaValida } from "../state/justificativa";
import type { PendenciaHumana } from "../types";

const ROTULO_ACAO: Record<string, string> = { reaprovar: "reaprovar por quem tem alçada", estornar: "estornar",
  reclassificar: "reclassificar a competência" };

interface Props {
  pendencia: PendenciaHumana;
  interativo: boolean;
  quem?: string; // pessoa autenticada que está decidindo (a decisão fica registrada no nome dela)
  aviso?: string; // por que esta conta não pode decidir
  aoDecidir: (decisao: string, justificativa: string) => void;
  aoFechar: () => void;
}

export function DecisaoHumana({ pendencia, interativo, aoDecidir, aoFechar, quem, aviso }: Props) {
  const [justificativa, setJustificativa] = useState("");
  const podeCorrigir = pendencia.opcoes.includes("corrigir");
  const podeWaiver = pendencia.opcoes.includes("waiver"); // a política pode negar (ex.: reincidência, POL-06)
  return (
    <Dialog open onClose={aoFechar} maxWidth="sm" fullWidth aria-labelledby="titulo-decisao">
      <DialogTitle id="titulo-decisao">
        <Stack direction="row" spacing={1} alignItems="center">
          <GavelIcon color="error" />
          <span>Veto do AG-CIN · {pendencia.solicitacao}</span>
          {pendencia.competencia && <Chip size="small" label={pendencia.competencia} />}
        </Stack>
      </DialogTitle>
      <DialogContent dividers>
        <Typography variant="body2" sx={{ mb: 1 }}>
          O Agente de Controles Internos vetou a publicação. O Orquestrador aguarda a sua decisão no ticket
          {" "}<b>{pendencia.conversation_id}</b> (uso único, com prazo); quem reavalia o pacote é o próprio AG-CIN.
        </Typography>
        {quem && <Alert severity="info" sx={{ mb: 1, py: 0 }}>Você decide como <b>{quem}</b>. A decisão fica registrada
          no seu nome; se você criou ou aprovou o lançamento vetado, ou fez este pedido, a política recusa.</Alert>}
        {aviso && <Alert severity="warning" sx={{ mb: 1, py: 0 }}>{aviso}</Alert>}
        <Typography variant="h3" component="h3">Achados</Typography>
        <List dense>
          {pendencia.achados.map((a) => (
            <ListItem key={`${a.regra}-${a.lancamento}`} disableGutters>
              <ListItemText primary={<><b>{a.regra}</b> em {a.lancamento}</>} secondary={a.evidencia} />
              <Chip size="small" variant="outlined" color={a.severidade === "critica" ? "error" : "default"}
                label={a.severidade === "critica" ? "crítica" : "não crítica"} />
            </ListItem>
          ))}
        </List>
        {podeCorrigir && (
          <>
            <Typography variant="h3" component="h3">Correções sugeridas pelo AG-CIN</Typography>
            <List dense>
              {pendencia.correcoes_sugeridas.map((c) => (
                <ListItem key={c.lancamento} disableGutters>
                  <ListItemText primary={`${c.lancamento}: ${ROTULO_ACAO[c.acao] ?? c.acao}`}
                    secondary={c.regras.join(", ")} />
                </ListItem>
              ))}
            </List>
          </>
        )}
        {interativo ? (
          <TextField label="Justificativa" fullWidth multiline minRows={2}
            helperText={podeWaiver ? "Obrigatória para waiver: mínimo de 10 caracteres e duas palavras diferentes (POL-04)"
              : "Waiver não admitido pela política para este veto (ex.: reincidência, POL-06): corrija ou bloqueie"}
            value={justificativa} onChange={(e) => setJustificativa(e.target.value)} sx={{ mt: 1 }}
            placeholder="ex.: risco aceito; lançamento será corrigido no próximo ciclo" />
        ) : (
          <Alert severity="info">Replay: a decisão já está gravada no trace; avance para vê-la.</Alert>
        )}
      </DialogContent>
      <DialogActions sx={{ flexWrap: "wrap", gap: 1 }}>
        <Button onClick={aoFechar}>Decidir depois</Button>
        {interativo && (
          <>
            <Button color="error" variant="outlined" onClick={() => aoDecidir("bloquear", justificativa)}>Bloquear</Button>
            <Button variant="outlined" disabled={!podeWaiver || !justificativaValida(justificativa)}
              onClick={() => aoDecidir("waiver", justificativa)}>Waiver (aceitar o risco)</Button>
            {podeCorrigir && pendencia.correcoes_sugeridas.length > 1 && (
              <Button variant="outlined" onClick={() => aoDecidir("corrigir_parcial", justificativa)}>
                Corrigir só a primeira</Button>)}
            {podeCorrigir && <Button variant="contained" onClick={() => aoDecidir("corrigir", justificativa)}>
              Corrigir no ERP</Button>}
          </>
        )}
      </DialogActions>
    </Dialog>
  );
}
