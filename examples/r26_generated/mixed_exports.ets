
export interface IConfig {
  apiUrl: string
  timeout: number
}

export type Status = 'active' | 'inactive'

export class ConfigManager {
  private static instance: ConfigManager
  private config: IConfig
  
  private constructor() {
    this.config = {
      apiUrl: 'https://api.example.com',
      timeout: 30000
    }
  }
  
  static getInstance(): ConfigManager {
    if (!ConfigManager.instance) {
      ConfigManager.instance = new ConfigManager()
    }
    return ConfigManager.instance
  }
  
  getConfig(): IConfig {
    return this.config
  }
  
  updateConfig(newConfig: Partial<IConfig>): void {
    this.config = { ...this.config, ...newConfig }
  }
}

export function createConfigManager(): ConfigManager {
  return ConfigManager.getInstance()
}

export const DEFAULT_TIMEOUT = 30000
