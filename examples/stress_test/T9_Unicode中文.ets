
@Component
struct 国际化页面 {
  @State 用户名: string = '张三'
  @State 数量: number = 42

  build() {
    Column() {
      Text('你好世界 ' + this.用户名)
      Text('数量: ' + this.数量.toString())
      Button('点击')
        .onClick(() => {
          this.处理点击()
        })
    }
  }

  private 处理点击(): void {
    this.数量++
    this.更新显示()
  }

  private 更新显示(): void {
    console.info('更新: ' + this.数量)
  }
}
