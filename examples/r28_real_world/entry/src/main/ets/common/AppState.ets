
// 全局状态管理
export class AppState {
  private static instance: AppState
  private state: Map<string, any> = new Map()
  private listeners: Map<string, ((value: any) => void)[]> = new Map()
  
  private constructor() {}
  
  static getInstance(): AppState {
    if (!AppState.instance) {
      AppState.instance = new AppState()
    }
    return AppState.instance
  }
  
  get<T>(key: string, defaultValue: T): T {
    return this.state.get(key) ?? defaultValue
  }
  
  set<T>(key: string, value: T): void {
    this.state.set(key, value)
    this.notify(key, value)
  }
  
  subscribe(key: string, listener: (value: any) => void): () => void {
    if (!this.listeners.has(key)) {
      this.listeners.set(key, [])
    }
    this.listeners.get(key)!.push(listener)
    return () => {
      const arr = this.listeners.get(key)
      if (arr) {
        this.listeners.set(key, arr.filter(l => l !== listener))
      }
    }
  }
  
  private notify(key: string, value: any): void {
    const arr = this.listeners.get(key)
    if (arr) {
      arr.forEach(l => l(value))
    }
  }
  
  clear(): void {
    this.state.clear()
    this.listeners.clear()
  }
}

// 用户状态
export class UserState {
  private appState: AppState = AppState.getInstance()
  
  isLoggedIn(): boolean {
    return this.appState.get('isLoggedIn', false)
  }
  
  setLoggedIn(value: boolean): void {
    this.appState.set('isLoggedIn', value)
  }
  
  getUserId(): string {
    return this.appState.get('userId', '')
  }
  
  setUserId(id: string): void {
    this.appState.set('userId', id)
  }
  
  logout(): void {
    this.setLoggedIn(false)
    this.setUserId('')
  }
}

// 主题状态
export class ThemeState {
  private appState: AppState = AppState.getInstance()
  
  isDarkMode(): boolean {
    return this.appState.get('darkMode', false)
  }
  
  setDarkMode(value: boolean): void {
    this.appState.set('darkMode', value)
  }
  
  toggleTheme(): void {
    this.setDarkMode(!this.isDarkMode())
  }
}
