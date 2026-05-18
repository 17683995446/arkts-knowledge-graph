/**
 * 复杂组件测试 - 各种嵌套、条件渲染、循环
 */

// 导入
import { UserModel, AdminModel } from '../models/UserModel'
import type { UserInfo, UserConfig } from '../models/Types'

// 简单组件
@Component
export struct SimpleButton {
    @Prop label: string = 'Button'
    @Prop disabled: boolean = false
    private onClick?: () => void

    build() {
        Button(this.label)
            .enabled(!this.disabled)
            .onClick(() => this.onClick?.())
    }
}

// 带状态的组件
@Component
export struct StatefulCard {
    @State private isExpanded: boolean = false
    @Prop title: string = ''
    @Prop content: string = ''

    build() {
        Column() {
            Row() {
                Text(this.title)
                    .fontSize(16)
                    .fontWeight(FontWeight.Bold)
                Blank()
                Text(this.isExpanded ? '收起' : '展开')
                    .fontSize(12)
                    .fontColor('#007AFF')
            }
            .width('100%')
            .padding(12)
            .onClick(() => {
                this.isExpanded = !this.isExpanded
            })

            if (this.isExpanded) {
                Text(this.content)
                    .fontSize(14)
                    .padding({ left: 12, right: 12, bottom: 12 })
            }
        }
        .width('100%')
        .borderRadius(8)
        .backgroundColor('#f5f5f5')
    }
}

// 列表项组件
@Component
export struct UserListItem {
    @Prop user: UserInfo = { id: '', name: '', email: '' }
    private onItemClick?: (user: UserInfo) => void
    private onItemLongPress?: (user: UserInfo) => void

    build() {
        Row() {
            Image(this.user.avatar || 'default_avatar.png')
                .width(40)
                .height(40)
                .borderRadius(20)

            Column() {
                Text(this.user.name)
                    .fontSize(14)
                    .fontWeight(FontWeight.Medium)
                Text(this.user.email)
                    .fontSize(12)
                    .fontColor('#999')
            }
            .alignItems(HorizontalAlign.Start)
            .layoutWeight(1)
            .margin({ left: 12 })

            Text(this.getStatusText())
                .fontSize(12)
                .padding({ left: 8, right: 8, top: 4, bottom: 4 })
                .borderRadius(4)
                .backgroundColor(this.getStatusColor())
        }
        .width('100%')
        .padding(12)
        .onClick(() => this.onItemClick?.(this.user))
        .gesture(
            LongPressGesture()
                .onAction(() => this.onItemLongPress?.(this.user))
        )
    }

    private getStatusText(): string {
        switch (this.user.status) {
            case 'active': return '活跃'
            case 'inactive': return '离线'
            case 'pending': return '待审核'
            default: return '未知'
        }
    }

    private getStatusColor(): string {
        switch (this.user.status) {
            case 'active': return '#E8F5E9'
            case 'inactive': return '#FFEBEE'
            case 'pending': return '#FFF3E0'
            default: return '#F5F5F5'
        }
    }
}

// 复杂嵌套组件
@Component
export struct ComplexLayout {
    @State private selectedIndex: number = 0
    @State private items: string[] = ['Item 1', 'Item 2', 'Item 3']
    @Link private globalState: { count: number, theme: string }

    build() {
        Stack() {
            // 背景层
            Column()
                .width('100%')
                .height('100%')
                .backgroundColor(this.globalState.theme === 'dark' ? '#1a1a1a' : '#ffffff')

            // 内容层
            Column() {
                // 顶部导航
                this.buildNavigation()

                // 主内容区
                Row() {
                    // 侧边栏
                    this.buildSidebar()

                    // 内容区
                    this.buildContent()
                }
                .layoutWeight(1)

                // 底部栏
                this.buildFooter()
            }
            .width('100%')
            .height('100%')
        }
    }

    @Builder
    buildNavigation(): void {
        Row() {
            ForEach(['首页', '列表', '设置'], (item: string, index: number) => {
                Text(item)
                    .fontSize(14)
                    .fontColor(this.selectedIndex === index ? '#007AFF' : '#333')
                    .padding({ left: 16, right: 16, top: 12, bottom: 12 })
                    .onClick(() => {
                        this.selectedIndex = index
                    })
            })
        }
        .width('100%')
        .height(50)
        .backgroundColor('#f5f5f5')
    }

    @Builder
    buildSidebar(): void {
        Column() {
            ForEach(this.items, (item: string, index: number) => {
                Text(item)
                    .width('100%')
                    .padding(12)
                    .backgroundColor(this.selectedIndex === index ? '#e0e0e0' : 'transparent')
                    .onClick(() => {
                        this.selectedIndex = index
                    })
            })

            Blank()

            Button('添加')
                .width('80%')
                .onClick(() => {
                    this.addItem()
                })
        }
        .width(200)
        .height('100%')
        .backgroundColor('#fafafa')
    }

    @Builder
    buildContent(): void {
        Column() {
            if (this.selectedIndex < this.items.length) {
                Text(`当前选中: ${this.items[this.selectedIndex]}`)
                    .fontSize(18)
                    .margin(20)

                Text(`全局计数: ${this.globalState.count}`)
                    .fontSize(16)
                    .margin(10)

                Row() {
                    Button('-')
                        .onClick(() => {
                            this.globalState.count--
                        })

                    Button('+')
                        .onClick(() => {
                            this.globalState.count++
                        })
                }
            } else {
                Text('请选择一个项目')
                    .fontSize(16)
                    .fontColor('#999')
            }
        }
        .layoutWeight(1)
        .height('100%')
        .justifyContent(FlexAlign.Center)
    }

    @Builder
    buildFooter(): void {
        Row() {
            Text('© 2024 ArkTS Knowledge Graph')
                .fontSize(12)
                .fontColor('#999')
        }
        .width('100%')
        .height(40)
        .justifyContent(FlexAlign.Center)
        .backgroundColor('#f5f5f5')
    }

    private addItem(): void {
        this.items.push(`Item ${this.items.length + 1}`)
    }
}

// 带动画的组件
@Component
export struct AnimatedCard {
    @State private scale: number = 1
    @State private opacity: number = 1
    @Prop title: string = ''

    build() {
        Column() {
            Text(this.title)
                .fontSize(16)
        }
        .width(200)
        .height(100)
        .backgroundColor('#007AFF')
        .borderRadius(12)
        .scale({ x: this.scale, y: this.scale })
        .opacity(this.opacity)
        .onTouch((event) => {
            if (event.type === TouchType.Down) {
                this.scale = 0.95
                this.opacity = 0.8
            } else if (event.type === TouchType.Up) {
                this.scale = 1
                this.opacity = 1
            }
        })
    }
}

// 自定义弹窗组件
@CustomDialog
export struct CustomAlertDialog {
    controller: CustomDialogController
    @State title: string = '提示'
    @State message: string = ''
    @State confirmText: string = '确定'
    @State cancelText: string = '取消'
    private onConfirm?: () => void
    private onCancel?: () => void

    build() {
        Column() {
            Text(this.title)
                .fontSize(18)
                .fontWeight(FontWeight.Bold)
                .margin({ bottom: 12 })

            Text(this.message)
                .fontSize(14)
                .fontColor('#666')
                .margin({ bottom: 24 })

            Row() {
                Button(this.cancelText)
                    .width('45%')
                    .backgroundColor('#f5f5f5')
                    .fontColor('#333')
                    .onClick(() => {
                        this.controller.close()
                        this.onCancel?.()
                    })

                Button(this.confirmText)
                    .width('45%')
                    .onClick(() => {
                        this.controller.close()
                        this.onConfirm?.()
                    })
            }
            .width('100%')
            .justifyContent(FlexAlign.SpaceBetween)
        }
        .padding(24)
        .backgroundColor('#ffffff')
        .borderRadius(12)
    }
}

// Builder函数测试
@Builder
function buildSimpleText(text: string): void {
    Text(text)
        .fontSize(14)
        .fontColor('#333')
}

@Builder
function buildComplexItem(data: { title: string; subtitle: string; icon: string }): void {
    Row() {
        Image(data.icon)
            .width(24)
            .height(24)

        Column() {
            Text(data.title)
                .fontSize(14)
            Text(data.subtitle)
                .fontSize(12)
                .fontColor('#999')
        }
        .alignItems(HorizontalAlign.Start)
        .margin({ left: 8 })
    }
    .width('100%')
    .padding(12)
}

// 样式装饰器测试
@Extend(Text)
function primaryTextStyle() {
    .fontSize(16)
    .fontColor('#007AFF')
    .fontWeight(FontWeight.Medium)
}

@Extend(Button)
function primaryButtonStyle() {
    .width('100%')
    .height(44)
    .backgroundColor('#007AFF')
    .borderRadius(8)
}

@Styles
function cardStyle() {
    .width('100%')
    .padding(16)
    .backgroundColor('#ffffff')
    .borderRadius(12)
    .shadow({ radius: 8, color: '#1a000000', offsetX: 0, offsetY: 2 })
}
