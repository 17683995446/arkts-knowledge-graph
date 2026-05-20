
export class Model3 {
  private id: number = 3
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
