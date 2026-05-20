
class 用户管理器 {
  private 用户列表: string[] = []
  
  添加用户(用户名: string): void {
    this.验证用户(用户名)
    this.用户列表.push(用户名)
  }
  
  private 验证用户(用户名: string): boolean {
    return 用户名.length > 0
  }
  
  获取数量(): number {
    return this.用户列表.length
  }
}
