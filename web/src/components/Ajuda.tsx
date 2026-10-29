// "Como usar": guia curto e legenda do escritório (abre na primeira visita e pelo botão de ajuda).
import {
  Button, Dialog, DialogActions, DialogContent, DialogTitle, List, ListItem, ListItemText, Stack, Typography,
} from "@mui/material";

const PASSOS = [
  ["Escolha o cenário e o porte", "Na barra de controles. “expediente_sma” é um dia inteiro da SMA; em “Dados da empresa” escolha micro, pequena, média ou grande, ou envie a planilha da sua empresa sem ERP."],
  ["Clique num agente", "Na planta ou nos chips. O painel à direita mostra a mente dele: intenções, deliberações (opções, utilidade e motivo de cada descarte), crenças e decisões."],
  ["Siga os badges", "Número no agente = novidades que você ainda não viu; número nas abas da mente = itens novos; sino vermelho = veto aguardando a sua decisão."],
  ["Decida como humano", "Ao vivo, o sino abre o veto do AG-CIN: corrigir no ERP (o AG-CIN reavalia), waiver com justificativa ou bloquear."],
  ["Peça e provoque falhas", "Ao vivo: “+ Novo pedido” (barra de controles ou painel do Solicitante) cria um pedido; o botão ⏻ no chip do agente (ou “Desligar agente” no painel) tira o agente de operação e os outros reagem (timeout, reenvio, replanejamento). O Orquestrador e os humanos não podem ser desligados."],
  ["Clique no que tem número", "Fontes de dados (ERP, Planilhas, Normas) mostram as chamadas MCP com proveniência; “Períodos” mostra as reservas de fechamento."],
  ["Compare", "A aba “SMA × workflow” mostra o mesmo conjunto de seeds no SMA e no workflow centralizado."],
];

const LEGENDA = [
  ["Envelope azul", "delegação (PROT-DEL)"], ["Envelope verde-água", "consulta entre especialistas (PROT-QRY)"],
  ["Envelope violeta", "conformidade e veto (PROT-CMP)"], ["Traço marrom pontilhado", "chamada a uma fonte de dados (MCP) ou reserva de período"],
  ["✕ caindo", "mensagem perdida (falha injetada ou agente fora)"], ["Anel tracejado", "agente trabalhando"],
  ["Carimbo VETO", "AG-CIN mantém o veto até correção, waiver ou prazo"],
];

export function Ajuda({ aberta, aoFechar }: { aberta: boolean; aoFechar: () => void }) {
  return (
    <Dialog open={aberta} onClose={aoFechar} maxWidth="md" fullWidth aria-labelledby="titulo-ajuda">
      <DialogTitle id="titulo-ajuda">Como usar o escritório da SMA</DialogTitle>
      <DialogContent dividers>
        <Stack direction={{ xs: "column", md: "row" }} spacing={3}>
          <List dense sx={{ flex: 3 }}>
            {PASSOS.map(([t, d], i) => (
              <ListItem key={t} disableGutters alignItems="flex-start">
                <ListItemText primary={`${i + 1}. ${t}`} secondary={d} />
              </ListItem>
            ))}
          </List>
          <List dense sx={{ flex: 2 }}>
            <Typography variant="h3" component="h3" sx={{ mb: 1 }}>Legenda</Typography>
            {LEGENDA.map(([t, d]) => (
              <ListItem key={t} disableGutters><ListItemText primary={t} secondary={d} /></ListItem>
            ))}
          </List>
        </Stack>
      </DialogContent>
      <DialogActions><Button variant="contained" onClick={aoFechar}>Entendi</Button></DialogActions>
    </Dialog>
  );
}
