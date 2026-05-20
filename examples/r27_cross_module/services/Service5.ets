
export class Service5 {
  private id: number = 5
  
  process(): void {
    console.info('Service5 processing')
  }
  
  getId(): number {
    return this.id
  }
}
