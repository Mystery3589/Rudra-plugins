export interface ParamSchema {
  name: string;
  is_argument: boolean;
  is_flag: boolean;
  flags: string[];
  type: 'bool' | 'int' | 'float' | 'choice' | 'path' | 'string';
  choices: string[] | null;
  required: boolean;
  default: any;
  help: string;
}

export interface CommandSchema {
  name: string;
  full_path: string[];
  command_str: string;
  help: string;
  params: ParamSchema[];
}

export interface SchemaData {
  groups: Record<string, CommandSchema[]>;
  group_names: string[];
}

export interface SystemStatus {
  os: string;
  platform_release: string;
  machine: string;
  has_nopasswd_sudo: boolean;
  is_local: boolean;
  auth_required: boolean;
}

export interface HistoryRecord {
  id: string;
  command: string;
  args: string[];
  exit_code: number;
  duration_sec: number;
  timestamp: string;
  timestamp_epoch: number;
  output_snippet: string;
}

export type ThemeMode = 'theme-indigo' | 'theme-tokyo' | 'theme-cyberpunk' | 'theme-matrix';
