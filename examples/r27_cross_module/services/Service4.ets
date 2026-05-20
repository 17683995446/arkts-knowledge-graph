
export class Service4 {
  private id: number = 4
  
  process(): void {
    console.info('Service4 processing')
  }
  
  getId(): number {
    return this.id
  }
}
