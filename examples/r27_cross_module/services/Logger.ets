
export class Logger {
  private level: string = 'INFO'
  
  setLevel(l: string): void {
    this.level = l
  }
  
  log(msg: string): void {
    console.info(`[${this.level}] ${msg}`)
  }
}
