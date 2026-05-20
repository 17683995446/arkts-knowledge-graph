
@Data
class UserEntity {
  private _id: number = 0
  private _name: string = ''
  private _email: string = ''
  private _createdAt: Date = new Date()
  private _updatedAt: Date = new Date()
  
  get id(): number { return this._id }
  set id(value: number) { this._id = value }
  
  get name(): string { return this._name }
  set name(value: string) { this._name = value }
  
  get email(): string { return this._email }
  set email(value: string) { this._email = value }
  
  get createdAt(): Date { return this._createdAt }
  set createdAt(value: Date) { this._createdAt = value }
  
  get updatedAt(): Date { return this._updatedAt }
  set updatedAt(value: Date) { this._updatedAt = value }
  
  updateTimestamp(): void {
    this._updatedAt = new Date()
  }
}
