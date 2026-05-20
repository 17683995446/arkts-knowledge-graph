
export class Product {
  constructor(
    public id: string,
    public name: string,
    public price: number
  ) {}
  
  calculateDiscount(percent: number): number {
    return this.price * (1 - percent / 100)
  }
}
