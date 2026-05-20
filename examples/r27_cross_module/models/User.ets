
export class User {
  constructor(
    public id: string,
    public name: string,
    public email: string
  ) {}
  
  validate(): boolean {
    return this.id.length > 0 && this.email.includes('@')
  }
}
