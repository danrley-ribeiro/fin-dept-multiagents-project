// O aprovador humano decide sobre o veto do AG-CIN: corrigir (aplica as correções sugeridas), waiver ou bloquear.
import GavelIcon from "@mui/icons-material/Gavel";
import {
  Alert, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, List, ListItem, ListItemText, Stack,
  TextField, Typography,
} from "@mui/material";
import { useState } from "react";
import type { PendenciaHumana } from "../types";

const ROTULO_ACAO: Record<string, string> = { reaprovar: "reaprovar por quem tem alçada", estornar: "estornar",
  reclassificar: "reclassificar a competência" };

interface Props {
  pendencia: PendenciaHumana;
  interativo: boolean;
  aoDecidir: (decisao: string, justificativa: string) => void;
  aoFechar: () => void;
}

export function DecisaoHumana({ pendencia, interativo, aoDecidir, aoFechar }: Props) {
  const [justificativa, setJustificativa] = useState("");
  const podeCorrigir = pendencia.opcoes.includes("corrigir");
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
          O Agente de Controles Internos vetou a publicação. O Orquestrador aguarda a sua decisão; quem reavalia o
          pacote é o próprio AG-CIN.
        </Typography>
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
          <TextField label="Justificativa" helperText="Obrigatória para waiver" fullWidth multiline minRows={2}
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
            <Button color="error" variant="outlined" onClick={() => aoDecidir("nenhuma", justificativa)}>Bloquear</Button>
            <Button variant="outlined" disabled={!justificativa.trim()}
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
