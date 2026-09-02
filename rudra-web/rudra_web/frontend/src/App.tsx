import React, { useState, useEffect, useRef } from "react";
import { NavigationRail, ActiveTab } from "./components/NavigationRail";
import { DashboardView } from "./views/DashboardView";
import { CommandStudioView } from "./views/CommandStudioView";
import { TerminalView } from "./views/TerminalView";
import { OracleView } from "./views/OracleView";
import { HistoryView } from "./components/HistoryView";
import { CommandPalette } from "./components/CommandPalette";
import { SudoModal } from "./components/SudoModal";
import { TerminalDrawer } from "./components/TerminalDrawer";
import { SchemaData, CommandSchema, SystemStatus, ThemeMode } from "./types/schema";
import { Terminal as Xterm } from "@xterm/xterm";

const THEMES: ThemeMode[] = ["theme-indigo", "theme-tokyo", "theme-cyberpunk", "theme-matrix"];

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>("dashboard");
  const [schema, setSchema] = useState<SchemaData | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [currentGroup, setCurrentGroup] = useState<string>("system");
  const [currentCmd, setCurrentCmd] = useState<CommandSchema | null>(null);
  const [formValues, setFormValues] = useState<Record<string, any>>({});
  const [theme, setTheme] = useState<ThemeMode>("theme-indigo");
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);
  const [isSudoOpen, setIsSudoOpen] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isRunning, setIsRunning] = useState(false);

  // Two terminal refs: fullscreen tab terminal & slide-up drawer terminal
  const termInstanceRef = useRef<Xterm | null>(null);
  const drawerTermRef = useRef<Xterm | null>(null);
  const activeWsRef = useRef<WebSocket | null>(null);

  // Mouse hover spotlight
  useEffect(() => {
    const h = (e: MouseEvent) => {
      document.documentElement.style.setProperty("--mouse-x", `${e.clientX}px`);
      document.documentElement.style.setProperty("--mouse-y", `${e.clientY}px`);
    };
    window.addEventListener("mousemove", h);
    return () => window.removeEventListener("mousemove", h);
  }, []);

  // Load API data
  useEffect(() => {
    fetch("/api/status").then(r => r.json()).then(setStatus).catch(console.error);
    fetch("/api/schema").then(r => r.json()).then(data => {
      setSchema(data);
      if (data.group_names?.length) {
        const grp = data.group_names.includes("system") ? "system" : data.group_names[0];
        setCurrentGroup(grp);
        const cmds = data.groups[grp] || [];
        if (cmds.length) selectCommand(cmds[0]);
      }
    }).catch(console.error);
  }, []);

  // Ctrl+K global palette
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsPaletteOpen(prev => !prev);
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  const selectCommand = (cmd: CommandSchema) => {
    setCurrentCmd(cmd);
    const init: Record<string, any> = {};
    cmd.params.forEach(p => {
      init[p.name] = p.default !== null ? p.default : (p.type === "bool" || p.is_flag ? false : "");
    });
    setFormValues(init);
  };

  const writeToAll = (text: string, isWrite = true) => {
    const both = [drawerTermRef.current, termInstanceRef.current];
    both.forEach(t => { if (t) isWrite ? t.write(text) : t.writeln(text); });
  };

  const executeTokens = (tokens: string[]) => {
    if (!tokens?.length) return;
    setIsRunning(true);

    // On non-terminal tabs open the slide-up drawer
    if (activeTab !== "terminal") setIsDrawerOpen(true);

    const header = `\r\n\x1b[1;38;2;99;102;241m▶ Executing:\x1b[0m \x1b[1;32m${tokens.join(" ")}\x1b[0m\r\n`;
    writeToAll(header, true);

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/run`);
    activeWsRef.current = ws;

    ws.onopen = () => ws.send(JSON.stringify({ args: tokens }));

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === "stdout") {
          writeToAll(msg.data.replace(/\n/g, "\r\n"), true);
        } else if (msg.type === "exit") {
          const c = msg.exit_code === 0 ? "\x1b[1;32m" : "\x1b[1;31m";
          writeToAll(`\r\n${c}● Exited ${msg.exit_code} (${msg.duration}s)\x1b[0m\r\n`, true);
        } else if (msg.type === "error") {
          writeToAll(`\r\n\x1b[1;31m\u2716 Error: ${msg.data}\x1b[0m\r\n`, true);
        }
      } catch {
        writeToAll(evt.data, true);
      }
    };

    ws.onclose = () => setIsRunning(false);
    ws.onerror = () => {
      writeToAll("\r\n\x1b[1;31m\u2716 WebSocket disconnected.\x1b[0m\r\n", true);
      setIsRunning(false);
    };
  };

  const handleAbort = () => {
    activeWsRef.current?.close();
    writeToAll("\r\n\x1b[1;33m\u23f9 Execution terminated by user.\x1b[0m\r\n", true);
  };

  const handleCycleTheme = () => {
    const next = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];
    setTheme(next);
    document.body.className = next;
  };

  return (
    <div className="h-screen flex overflow-hidden bg-canvas text-slate-100 font-sans">
      <NavigationRail
        activeTab={activeTab}
        onTabChange={setActiveTab}
        status={status}
        theme={theme}
        onCycleTheme={handleCycleTheme}
        onOpenPalette={() => setIsPaletteOpen(true)}
        onOpenSudo={() => setIsSudoOpen(true)}
      />

      <div className="flex-1 flex overflow-hidden relative">
        {activeTab === "dashboard" && (
          <DashboardView status={status} onExecute={executeTokens} onNavigateTab={setActiveTab} />
        )}
        {activeTab === "studio" && (
          <CommandStudioView
            schema={schema}
            currentGroup={currentGroup}
            onSelectGroup={(g) => {
              setCurrentGroup(g);
              const cmds = schema?.groups[g] || [];
              if (cmds.length) selectCommand(cmds[0]);
            }}
            currentCmd={currentCmd}
            onSelectCmd={selectCommand}
            formValues={formValues}
            onParamChange={(name, val) => setFormValues(prev => ({ ...prev, [name]: val }))}
            onExecute={executeTokens}
            isRunning={isRunning}
            onAbort={handleAbort}
          />
        )}
        {activeTab === "terminal" && (
          <TerminalView
            onExecute={executeTokens}
            isRunning={isRunning}
            termInstanceRef={termInstanceRef}
          />
        )}
        {activeTab === "oracle" && (
          <OracleView onExecute={executeTokens} />
        )}
        {activeTab === "history" && (
          <HistoryView
            onBack={() => setActiveTab("dashboard")}
            onReRun={(args) => { setActiveTab("terminal"); executeTokens(args); }}
          />
        )}

        {/* Slide-up drawer — only on non-terminal tabs */}
        {activeTab !== "terminal" && (
          <TerminalDrawer
            isOpen={isDrawerOpen}
            onToggle={() => setIsDrawerOpen(prev => !prev)}
            isRunning={isRunning}
            onAbort={handleAbort}
            termInstanceRef={drawerTermRef}
          />
        )}
      </div>

      <CommandPalette
        isOpen={isPaletteOpen}
        onClose={() => setIsPaletteOpen(false)}
        schema={schema}
        onSelectCmd={(group, cmd) => {
          setCurrentGroup(group);
          selectCommand(cmd);
          setActiveTab("studio");
        }}
      />
      <SudoModal
        isOpen={isSudoOpen}
        onClose={() => setIsSudoOpen(false)}
        onSuccess={() => setStatus(prev => prev ? { ...prev, has_nopasswd_sudo: true } : null)}
      />
    </div>
  );
};
