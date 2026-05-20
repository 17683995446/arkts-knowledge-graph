
export class Model1 {
  private id: number = 1
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
