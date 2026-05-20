
export class Service1 {
  private id: number = 1
  
  process(): void {
    console.info('Service1 processing')
  }
  
  getId(): number {
    return this.id
  }
}
