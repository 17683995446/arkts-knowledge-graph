/**
 * 常量定义
 */

import { AppTheme } from '../models/Types'

// 应用常量
export class CommonConstants {
    static readonly APP_NAME: string = 'ArkTS Knowledge Graph Demo'
    static readonly APP_VERSION: string = '1.0.0'
    static readonly API_VERSION: string = 'v1'

    // 超时配置
    static readonly API_TIMEOUT: number = 30000
    static readonly REQUEST_RETRY: number = 3
    static readonly CACHE_TTL: number = 3600000 // 1小时

    // 分页配置
    static readonly DEFAULT_PAGE_SIZE: number = 20
    static readonly MAX_PAGE_SIZE: number = 100

    // 文件大小限制
    static readonly MAX_FILE_SIZE: number = 10 * 1024 * 1024 // 10MB
    static readonly MAX_IMAGE_SIZE: number = 5 * 1024 * 1024 // 5MB

    // 本地存储键
    static readonly STORAGE_KEYS = {
        AUTH_TOKEN: 'auth_token',
        REFRESH_TOKEN: 'refresh_token',
        USER_INFO: 'user_info',
        THEME: 'theme',
        LANGUAGE: 'language',
        CACHE_PREFIX: 'cache_'
    } as const

    // 路由路径
    static readonly ROUTES = {
        HOME: 'pages/MainPage',
        LOGIN: 'pages/LoginPage',
        USER_DETAIL: 'pages/UserDetailPage',
        SETTINGS: 'pages/SettingsPage',
        ABOUT: 'pages/AboutPage'
    } as const
}

// 主题配置
export enum AppTheme {
    LIGHT = 'light',
    DARK = 'dark',
    AUTO = 'auto'
}

// 主题颜色
export class ThemeColors {
    static readonly LIGHT = {
        background: '#ffffff',
        text: '#333333',
        primary: '#007AFF',
        secondary: '#5856D6',
        success: '#34C759',
        warning: '#FF9500',
        error: '#FF3B30',
        border: '#e0e0e0'
    }

    static readonly DARK = {
        background: '#1a1a1a',
        text: '#ffffff',
        primary: '#0A84FF',
        secondary: '#5E5CE6',
        success: '#30D158',
        warning: '#FFD60A',
        error: '#FF453A',
        border: '#333333'
    }
}

// HTTP状态码
export enum HttpStatus {
    OK = 200,
    CREATED = 201,
    NO_CONTENT = 204,
    BAD_REQUEST = 400,
    UNAUTHORIZED = 401,
    FORBIDDEN = 403,
    NOT_FOUND = 404,
    METHOD_NOT_ALLOWED = 405,
    REQUEST_TIMEOUT = 408,
    CONFLICT = 409,
    TOO_MANY_REQUESTS = 429,
    SERVER_ERROR = 500,
    BAD_GATEWAY = 502,
    SERVICE_UNAVAILABLE = 503,
    GATEWAY_TIMEOUT = 504
}

// 错误消息
export class ErrorMessages {
    static readonly NETWORK_ERROR: string = '网络连接失败，请检查网络设置'
    static readonly TIMEOUT_ERROR: string = '请求超时，请稍后重试'
    static readonly SERVER_ERROR: string = '服务器错误，请稍后重试'
    static readonly UNKNOWN_ERROR: string = '未知错误'
    static readonly AUTH_EXPIRED: string = '登录已过期，请重新登录'
    static readonly PERMISSION_DENIED: string = '没有权限执行此操作'
}

// 正则表达式
export class RegexPatterns {
    static readonly EMAIL: RegExp = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    static readonly PHONE: RegExp = /^1[3-9]\d{9}$/
    static readonly URL: RegExp = /^https?:\/\/[^\s]+$/
    static readonly ID_CARD: RegExp = /^\d{17}[\dXx]$/
    static readonly PASSWORD: RegExp = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,}$/
}
