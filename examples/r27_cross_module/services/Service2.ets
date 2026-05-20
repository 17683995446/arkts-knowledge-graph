
export class Service2 {
  private id: number = 2
  
  process(): void {
    console.info('Service2 processing')
  }
  
  getId(): number {
    return this.id
  }
}
