/**
 * 复杂入口页面 - 测试各种边界情况
 * 包含：多层嵌套、复杂装饰器、泛型、异步方法、生命周期
 */

// 导入测试
import { UserService, AuthService } from '../services/UserService'
import { UserModel, AdminModel } from '../models/UserModel'
import { HttpUtil, StorageUtil } from '../utils/HttpUtil'
import { CommonConstants, AppTheme } from '../common/Constants'
import type { UserInfo, UserConfig } from '../models/Types'
import * as Utils from '../utils/Index'

// 多装饰器测试
@Entry
@Component
@Reusable
@Observed
export struct MainPage {
    // 状态装饰器测试
    @State private message: string = 'Hello ArkTS'
    @State private count: number = 0
    @State private isLoading: boolean = false
    @State private userList: Array<UserInfo> = []
    @State private config: UserConfig | null = null
    
    @Link private globalCounter: number
    @Provide('theme') currentTheme: AppTheme = AppTheme.DARK
    @Consume('userToken') userToken: string
    
    @ObjectLink private userData: UserModel
    @Watch('onMessageChange') private watchedMessage: string = ''
    
    @BuilderParam private headerBuilder: () => void = this.defaultHeader
    @BuilderParam private footerBuilder: () => void
    
    @State private complexObject: {
        name: string
        age: number
        address: {
            city: string
            street: string
            zipCode: string
        }
        tags: string[]
    } = {
        name: 'Test',
        age: 25,
        address: { city: 'Beijing', street: 'Main St', zipCode: '100000' },
        tags: ['tag1', 'tag2']
    }

    // 私有属性
    private serviceName: string = 'MainPageService'
    private static instanceCount: number = 0
    protected protectedProp: string = 'protected'
    readonly readOnlyProp: string = 'readonly'

    // 生命周期方法
    aboutToAppear(): void {
        MainPage.instanceCount++
        this.initPage()
        this.loadUserData()
        this.subscribeEvents()
    }

    aboutToDisappear(): void {
        this.unsubscribeEvents()
        this.cleanup()
        MainPage.instanceCount--
    }

    onPageShow(): void {
        this.refreshData()
    }

    onPageHide(): void {
        this.saveState()
    }

    onBackPress(): boolean {
        return this.handleBackPress()
    }

    // 私有方法
    private initPage(): void {
        this.isLoading = true
        this.message = 'Initializing...'
        this.setupTheme()
    }

    private async loadUserData(): Promise<void> {
        try {
            const service = UserService.getInstance()
            const data = await service.fetchUserInfo(this.userToken)
            this.userList = data.users
            this.config = data.config
            this.processUserData(data)
        } catch (error) {
            this.handleError(error as Error)
        } finally {
            this.isLoading = false
        }
    }

    private processUserData(data: { users: UserInfo[], config: UserConfig }): void {
        data.users.forEach((user, index) => {
            this.validateUser(user)
            this.cacheUser(user, index)
        })
    }

    private validateUser(user: UserInfo): boolean {
        if (!user.id || !user.name) {
            return false
        }
        return user.email?.includes('@') ?? false
    }

    private cacheUser(user: UserInfo, index: number): void {
        StorageUtil.set(`user_${index}`, JSON.stringify(user))
    }

    private subscribeEvents(): void {
        EventBus.on('userUpdate', this.onUserUpdate.bind(this))
        EventBus.on('themeChange', this.onThemeChange.bind(this))
    }

    private unsubscribeEvents(): void {
        EventBus.off('userUpdate', this.onUserUpdate.bind(this))
        EventBus.off('themeChange', this.onThemeChange.bind(this))
    }

    private onUserUpdate(data: object): void {
        this.refreshData()
    }

    private onThemeChange(theme: AppTheme): void {
        this.currentTheme = theme
    }

    private setupTheme(): void {
        const savedTheme = StorageUtil.get('theme') as AppTheme
        if (savedTheme) {
            this.currentTheme = savedTheme
        }
    }

    private refreshData(): void {
        this.loadUserData()
    }

    private saveState(): void {
        StorageUtil.set('pageState', JSON.stringify({
            message: this.message,
            count: this.count
        }))
    }

    private handleBackPress(): boolean {
        if (this.hasUnsavedChanges()) {
            this.showConfirmDialog()
            return true
        }
        return false
    }

    private hasUnsavedChanges(): boolean {
        return this.message !== 'Hello ArkTS' || this.count !== 0
    }

    private showConfirmDialog(): void {
        AlertDialog.show({
            title: '确认退出',
            message: '有未保存的更改，确定要退出吗？',
            primaryButton: {
                value: '取消',
                action: () => {}
            },
            secondaryButton: {
                value: '确定',
                action: () => {
                    this.navigateToBack()
                }
            }
        })
    }

    private navigateToBack(): void {
        router.back()
    }

    private cleanup(): void {
        this.userList = []
        this.config = null
    }

    private handleError(error: Error): void {
        console.error('Error:', error.message)
        this.message = `Error: ${error.message}`
    }

    // 公共方法
    public incrementCounter(): void {
        this.count++
        this.globalCounter++
        this.notifyCounterChange()
    }

    public decrementCounter(): void {
        this.count--
        this.globalCounter--
        this.notifyCounterChange()
    }

    public resetCounter(): void {
        this.count = 0
        this.notifyCounterChange()
    }

    private notifyCounterChange(): void {
        EventBus.emit('counterChange', { count: this.count })
    }

    // 静态方法
    static getInstanceCount(): number {
        return MainPage.instanceCount
    }

    static async preloadData(): Promise<void> {
        const service = UserService.getInstance()
        await service.preloadCache()
    }

    // Getter/Setter
    get formattedMessage(): string {
        return `[${this.serviceName}] ${this.message}`
    }

    set formattedMessage(value: string) {
        this.message = value.replace(/^\[.*\]\s*/, '')
    }

    // Watch 回调
    private onMessageChange(newValue: string, oldValue: string): void {
        console.log(`Message changed from "${oldValue}" to "${newValue}"`)
    }

    // Builder 方法
    @Builder
    defaultHeader(): void {
        Row() {
            Text('Default Header')
                .fontSize(16)
                .fontWeight(FontWeight.Bold)
        }
        .width('100%')
        .height(50)
    }

    @Builder
    userItemBuilder(user: UserInfo, index: number): void {
        Row() {
            Text(user.name)
                .fontSize(14)
            Text(user.email ?? '')
                .fontSize(12)
                .fontColor('#999')
        }
        .width('100%')
        .padding(12)
        .onClick(() => this.onUserItemClick(user, index))
    }

    private onUserItemClick(user: UserInfo, index: number): void {
        router.pushUrl({
            url: 'pages/UserDetailPage',
            params: { userId: user.id, index: index }
        })
    }

    // 复杂 build 方法
    build() {
        Column() {
            // Header
            this.headerBuilder()

            // 搜索栏
            Row() {
                TextInput({ placeholder: '搜索...' })
                    .width('70%')
                    .onChange((value: string) => {
                        this.searchUsers(value)
                    })

                Button('搜索')
                    .width('25%')
                    .onClick(() => {
                        this.performSearch()
                    })
            }
            .width('100%')
            .padding(10)

            // 内容区域
            if (this.isLoading) {
                LoadingProgress()
                    .width(50)
                    .height(50)
            } else {
                Tabs() {
                    TabContent() {
                        this.buildUserListTab()
                    }
                    .tabBar('用户列表')

                    TabContent() {
                        this.buildSettingsTab()
                    }
                    .tabBar('设置')

                    TabContent() {
                        this.buildStatsTab()
                    }
                    .tabBar('统计')
                }
                .width('100%')
                .layoutWeight(1)
            }

            // 计数器区域
            Row() {
                Button('-')
                    .onClick(() => this.decrementCounter())

                Text(`${this.count}`)
                    .width(60)
                    .textAlign(TextAlign.Center)

                Button('+')
                    .onClick(() => this.incrementCounter())
            }
            .width('100%')
            .justifyContent(FlexAlign.Center)
            .padding(10)

            // Footer
            if (this.footerBuilder) {
                this.footerBuilder()
            }
        }
        .width('100%')
        .height('100%')
        .backgroundColor(this.currentTheme === AppTheme.DARK ? '#1a1a1a' : '#ffffff')
    }

    @Builder
    buildUserListTab(): void {
        List() {
            ForEach(this.userList, (user: UserInfo, index: number) => {
                ListItem() {
                    this.userItemBuilder(user, index)
                }
            }, (user: UserInfo) => user.id)
        }
        .width('100%')
        .layoutWeight(1)
        .divider({ strokeWidth: 1, color: '#e0e0e0' })
    }

    @Builder
    buildSettingsTab(): void {
        Scroll() {
            Column() {
                this.buildSettingItem('主题', () => this.toggleTheme())
                this.buildSettingItem('通知', () => this.toggleNotification())
                this.buildSettingItem('缓存', () => this.clearCache())
            }
            .width('100%')
        }
        .width('100%')
        .layoutWeight(1)
    }

    @Builder
    buildSettingItem(title: string, action: () => void): void {
        Row() {
            Text(title)
                .fontSize(16)
            Blank()
            Toggle({ type: ToggleType.Switch, isOn: false })
                .onChange((isOn: boolean) => {
                    action()
                })
        }
        .width('100%')
        .padding({ left: 16, right: 16, top: 12, bottom: 12 })
        .onClick(action)
    }

    @Builder
    buildStatsTab(): void {
        Grid() {
            ForEach(this.getStatsData(), (stat: { label: string, value: number }) => {
                GridItem() {
                    Column() {
                        Text(`${stat.value}`)
                            .fontSize(24)
                            .fontWeight(FontWeight.Bold)
                        Text(stat.label)
                            .fontSize(12)
                            .fontColor('#999')
                    }
                    .width('100%')
                    .height(80)
                    .justifyContent(FlexAlign.Center)
                }
            })
        }
        .columnsTemplate('1fr 1fr')
        .rowsTemplate('1fr 1fr')
        .width('100%')
        .layoutWeight(1)
    }

    private getStatsData(): Array<{ label: string, value: number }> {
        return [
            { label: '总用户', value: this.userList.length },
            { label: '计数', value: this.count },
            { label: '全局计数', value: this.globalCounter },
            { label: '实例数', value: MainPage.instanceCount }
        ]
    }

    private searchUsers(keyword: string): void {
        // 搜索逻辑
    }

    private performSearch(): void {
        // 执行搜索
    }

    private toggleTheme(): void {
        this.currentTheme = this.currentTheme === AppTheme.DARK 
            ? AppTheme.LIGHT 
            : AppTheme.DARK
        StorageUtil.set('theme', this.currentTheme)
    }

    private toggleNotification(): void {
        // 切换通知
    }

    private clearCache(): void {
        StorageUtil.clear()
        this.showToast('缓存已清除')
    }

    private showToast(message: string): void {
        promptAction.showToast({ message: message })
    }
}

// 泛型工具类测试
class GenericContainer<T> {
    private items: T[] = []

    add(item: T): void {
        this.items.push(item)
    }

    get(index: number): T | undefined {
        return this.items[index]
    }

    getAll(): T[] {
        return [...this.items]
    }

    find(predicate: (item: T) => boolean): T | undefined {
        return this.items.find(predicate)
    }

    filter(predicate: (item: T) => boolean): T[] {
        return this.items.filter(predicate)
    }

    map<U>(mapper: (item: T) => U): U[] {
        return this.items.map(mapper)
    }
}

// 抽象类测试
abstract class BaseViewModel<T> {
    protected data: T | null = null
    protected loading: boolean = false
    protected error: Error | null = null

    abstract fetchData(): Promise<T>
    abstract onDataLoaded(data: T): void

    async load(): Promise<void> {
        this.loading = true
        this.error = null
        try {
            this.data = await this.fetchData()
            this.onDataLoaded(this.data)
        } catch (e) {
            this.error = e as Error
        } finally {
            this.loading = false
        }
    }

    getData(): T | null {
        return this.data
    }

    isLoading(): boolean {
        return this.loading
    }

    getError(): Error | null {
        return this.error
    }
}

// 接口继承测试
interface IBaseEntity {
    id: string
    createdAt: number
    updatedAt: number
}

interface IUser extends IBaseEntity {
    name: string
    email: string
    avatar?: string
}

interface IAdmin extends IUser {
    role: 'admin' | 'super_admin'
    permissions: string[]
}

// 类型别名测试
type UserStatus = 'active' | 'inactive' | 'pending' | 'deleted'
type AsyncResult<T> = Promise<{ data: T; error: Error | null }>
type EventHandler<T> = (event: T) => void
type DeepPartial<T> = {
    [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P]
}

// 枚举测试
enum UserAction {
    CREATE = 'create',
    READ = 'read',
    UPDATE = 'update',
    DELETE = 'delete'
}

enum HttpStatus {
    OK = 200,
    CREATED = 201,
    BAD_REQUEST = 400,
    UNAUTHORIZED = 401,
    FORBIDDEN = 403,
    NOT_FOUND = 404,
    SERVER_ERROR = 500
}

// 命名空间测试
namespace AppEvents {
    export const USER_LOGIN = 'user:login'
    export const USER_LOGOUT = 'user:logout'
    export const DATA_REFRESH = 'data:refresh'

    export interface EventPayload {
        type: string
        timestamp: number
        data?: object
    }

    export function createEvent(type: string, data?: object): EventPayload {
        return {
            type,
            timestamp: Date.now(),
            data
        }
    }
}
