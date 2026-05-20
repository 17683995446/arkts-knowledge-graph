
export class Model10 {
  private id: number = 10
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
