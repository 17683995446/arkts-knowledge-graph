
import { UserModel } from '../models/UserModel'
import { UserService } from '../services/UserService'

export class UserViewModel {
  private user: UserModel = new UserModel()
  private service: UserService = new UserService()
  
  async loadUser(userId: string): Promise<void> {
    const data = await this.service.fetchUser(userId)
    this.user = UserModel.fromJson(data)
  }
  
  async updateUser(): Promise<boolean> {
    if (!this.user.validate()) {
      return false
    }
    return this.service.updateUser(this.user.toJson())
  }
  
  getUserName(): string {
    return this.user.name
  }
  
  getUserEmail(): string {
    return this.user.email
  }
}
