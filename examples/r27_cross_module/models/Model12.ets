
export class Model12 {
  private id: number = 12
  private data: string = ''
  
  getId(): number {
    return this.id
  }
  
  setData(d: string): void {
    this.data = d
  }
  
  getData(): string {
    return this.data
  }
}
