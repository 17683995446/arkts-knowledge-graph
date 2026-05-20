
export interface IUser {
  id: string
  name: string
  email: string
  avatar: string
  createdAt: string
}

export class UserModel implements IUser {
  id: string = ''
  name: string = ''
  email: string = ''
  avatar: string = ''
  createdAt: string = ''
  
  static fromJson(json: Record<string, any>): UserModel {
    const model = new UserModel()
    model.id = json.id as string
    model.name = json.name as string
    model.email = json.email as string
    model.avatar = json.avatar as string
    model.createdAt = json.createdAt as string
    return model
  }
  
  toJson(): Record<string, any> {
    return {
      id: this.id,
      name: this.name,
      email: this.email,
      avatar: this.avatar,
      createdAt: this.createdAt
    }
  }
  
  validate(): boolean {
    return this.id.length > 0 && this.email.includes('@')
  }
}
