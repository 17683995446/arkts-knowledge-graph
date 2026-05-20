
class ApiClient {
  private baseUrl: string = 'https://api.example.com'
  private timeout: number = 30000
  
  async getUsers(): Promise<UserResponse> {
    return this.request<UserResponse>('GET', '/users')
  }
  
  async getUser(id: string): Promise<UserResponse> {
    return this.request<UserResponse>('GET', `/users/${id}`)
  }
  
  async createUser(data: CreateUserRequest): Promise<UserResponse> {
    return this.request<UserResponse>('POST', '/users', data)
  }
  
  async updateUser(id: string, data: UpdateUserRequest): Promise<UserResponse> {
    return this.request<UserResponse>('PUT', `/users/${id}`, data)
  }
  
  async deleteUser(id: string): Promise<void> {
    return this.request<void>('DELETE', `/users/${id}`)
  }
  
  async getPosts(): Promise<PostResponse[]> {
    return this.request<PostResponse[]>('GET', '/posts')
  }
  
  async createPost(data: CreatePostRequest): Promise<PostResponse> {
    return this.request<PostResponse>('POST', '/posts', data)
  }
  
  private async request<T>(method: string, path: string, body?: Object): Promise<T> {
    console.info(`${method} ${this.baseUrl}${path}`)
    return {} as T
  }
}
