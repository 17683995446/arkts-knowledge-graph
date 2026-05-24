/**
 * 嵌套组件文件 - 深度 8
 */

import { NestedComponent9 } from './NestedComponent9';

@Component
export struct NestedComponent8 {
    build() {
        Column() {
            NestedComponent9()
            NestedComponent9()
        }
    }
}
