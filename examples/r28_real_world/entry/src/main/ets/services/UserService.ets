
export class UserService {
  private baseUrl: string = 'https://api.example.com'
  
  async fetchUser(userId: string): Promise<Record<string, any>> {
    // Simulate API call
    return {
      id: userId,
      name: 'Test User',
      email: 'test@example.com',
      avatar: '',
      createdAt: new Date().toISOString()
    }
  }
  
  async updateUser(data: Record<string, any>): Promise<boolean> {
    // Simulate API call
    return true
  }
  
  async deleteUser(userId: string): Promise<boolean> {
    return true
  }
}
