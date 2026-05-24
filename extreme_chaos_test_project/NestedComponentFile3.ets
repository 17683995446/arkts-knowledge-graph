/**
 * 嵌套组件文件 - 深度 3
 */

import { NestedComponent4 } from './NestedComponentFile4';

@Component
export struct NestedComponent3 {

    build() {
        Column() {
            NestedComponent4()
            NestedComponent4()
            NestedComponent4()
        }
    }

}
