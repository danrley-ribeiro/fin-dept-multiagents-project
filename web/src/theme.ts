// Tema Material Design (MUI) com as cores da SMA; o modo segue o sistema ou a escolha do usuário.
import { createTheme } from "@mui/material/styles";

export type ModoTema = "light" | "dark";

export function criarTema(modo: ModoTema) {
  const escuro = modo === "dark";
  return createTheme({
    palette: {
      mode: modo,
      primary: { main: escuro ? "#7fb2e5" : "#1F4E79" },
      secondary: { main: "#F2A900" },
      error: { main: escuro ? "#ef6b6b" : "#c62828" },
      warning: { main: escuro ? "#e0a440" : "#a86800" },
      success: { main: escuro ? "#5cc27f" : "#1d7a3a" },
      background: escuro ? { default: "#121211", paper: "#1a1a19" } : { default: "#f3f2ee", paper: "#fcfcfb" },
    },
    shape: { borderRadius: 10 },
    typography: {
      fontFamily: "Roboto, system-ui, -apple-system, 'Segoe UI', Arial, sans-serif",
      h1: { fontSize: "1.05rem", fontWeight: 600 },
      h2: { fontSize: "0.95rem", fontWeight: 600 },
      h3: { fontSize: "0.85rem", fontWeight: 600 },
    },
    components: {
      MuiPaper: { defaultProps: { variant: "outlined" } },
      MuiButton: { defaultProps: { disableElevation: true }, styleOverrides: { root: { textTransform: "none" } } },
      MuiTab: { styleOverrides: { root: { textTransform: "none", minHeight: 42 } } },
      MuiTooltip: { defaultProps: { arrow: true } },
      MuiChip: { styleOverrides: { root: { fontWeight: 500 } } },
    },
  });
}
