
export class Service3 {
  private id: number = 3
  
  process(): void {
    console.info('Service3 processing')
  }
  
  getId(): number {
    return this.id
  }
}
