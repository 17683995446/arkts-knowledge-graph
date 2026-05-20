
export class Logger {
  private prefix: string = ''
  
  setPrefix(p: string): void {
    this.prefix = p
  }
  
  log(msg: string): void {
    console.info(`[${this.prefix}] ${msg}`)
  }
  
  error(msg: string): void {
    console.error(`[${this.prefix}] ERROR: ${msg}`)
  }
  
  warn(msg: string): void {
    console.warn(`[${this.prefix}] WARN: ${msg}`)
  }
}
