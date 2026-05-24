/**
 * 嵌套组件文件 - 深度 2
 */

import { NestedComponent3 } from './NestedComponent3';

@Component
export struct NestedComponent2 {
    build() {
        Column() {
            NestedComponent3()
            NestedComponent3()
        }
    }
}
