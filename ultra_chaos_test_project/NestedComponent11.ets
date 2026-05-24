/**
 * 嵌套组件文件 - 深度 11
 */

import { NestedComponent12 } from './NestedComponent12';

@Component
export struct NestedComponent11 {
    build() {
        Column() {
            NestedComponent12()
            NestedComponent12()
        }
    }
}
