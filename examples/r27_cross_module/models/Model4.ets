
export class Model4 {
  private id: number = 4
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
