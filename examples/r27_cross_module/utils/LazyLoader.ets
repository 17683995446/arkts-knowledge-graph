
export class LazyLoader {
  private modules: Map<string, any> = new Map()
  
  async load(name: string): Promise<any> {
    if (this.modules.has(name)) {
      return this.modules.get(name)
    }
    
    const module = await import(`./${name}`)
    this.modules.set(name, module)
    return module
  }
  
  has(name: string): boolean {
    return this.modules.has(name)
  }
  
  clear(): void {
    this.modules.clear()
  }
}
