/**
 * 嵌套组件文件 - 深度 4
 */

import { NestedComponent5 } from './NestedComponent5';

@Component
export struct NestedComponent4 {
    build() {
        Column() {
            NestedComponent5()
            NestedComponent5()
        }
    }
}
